import pandas as pd
import math
from abc import ABC, abstractmethod
import sys


class Model(ABC):

    # return list of valid trades to perform if trade condition met
    @abstractmethod
    def instruct():
        # check difference against params to determine whether to rebalance
        return


class McapModel(Model):

    def __init__(self, assets, params, market_data):
        self.assets = assets
        self.params = {x: params[x][0] for x in params}
        for x in self.params:
            if "," in str(self.params[x]):
                self.params[x] = self.params[x].split(',')

        self.market_data = market_data

        gains = {}
        for symbol in self.assets:
            try:
                gains[symbol] = (self.assets[symbol]['new_price']-self.assets[symbol]
                                 ['avg_price']) / self.assets[symbol]['avg_price']
            except(ZeroDivisionError):
                gains[symbol] = 0
        self.gains = gains
        self.fiat_total = sum([self.assets[asset]['new_price']
                              * self.assets[asset]['tot'] for asset in self.assets])

        self.balanced_pf = self.balanced_portfolio()
        self.diff_matrix = self.get_diff_matrix(self.balanced_pf)

    def get_token_diff(self):
        data = {}

        for element in self.diff_matrix:
            if element not in self.assets.keys():
                pass
            else:
                data[element] = round(float(self.diff_matrix[element] /
                                            self.assets[element]['new_price']), 3)

        data = pd.DataFrame(data, index=[0]).transpose()
        data.columns = ['token diff']
        return data

    def get_diff_matrix(self, balanced):
        # do some calculatons with input_params
        diffs = {}
        for element in balanced:
            element = element.strip()
            try:
                diffs[element] = (self.assets[element]['tot']*self.assets[element]
                                  ['new_price']) - balanced[element]
            except(KeyError) as e:
                diffs[element] = -balanced[element]
        for element in self.assets:
            if element not in diffs.keys():
                diffs[element] = self.assets[element]['tot'] * \
                    self.assets[element]['new_price']
        return diffs

    def balanced_portfolio(self):
        weights = {}
        banned_coins = self.params['banned_coins']
        total = 1
        # handpicked-hard
        hard_hp = self.params['hard_hp']
        hard_hp_amts = self.params['hard_hp_amts']
        for i in range(len(hard_hp)):
            banned_coins.append(hard_hp[i])
            total -= float(hard_hp_amts[i])
            weights[hard_hp[i]] = float(hard_hp_amts[i])

        min_profit = float(self.params['profit_pct'])
        min_trade_fiat = float(self.params['min_trade_fiat'])
        self.dynamic_mcap = math.floor(
            (min_profit * self.fiat_total * total)/min_trade_fiat)
        self.mcap_coins = min(max(int(self.params['min_mcap_coins']), self.dynamic_mcap), int(
            self.params['max_mcap_coins']))
        self.fraction = total/self.mcap_coins
        lots_open = self.mcap_coins
        if self.params['handpicked_mcap']:
            symbols = self.params['handpicked_mcap']
            for symbol in symbols:
                weights[symbol] = self.fraction
                banned_coins.append(symbol)
                lots_open -= 1

        skipped = None
        for coin in self.market_data:
            symbol = coin['symbol']
            if lots_open < 1:
                break
            # deal with skipped if we picked an alternative last iteration
            # not a problem since this coin will be banned or already picked
            if skipped:
                weights[skipped] = self.fraction
                lots_open -= 1
                banned_coins.append(skipped)
                skipped = None
                continue
            if symbol not in banned_coins:
                # missing coin, see if we have an almost as good coin already
                if symbol not in self.assets.keys():
                    for next_coin in self.market_data:
                        next_symbol = next_coin['symbol']
                        if next_symbol not in banned_coins and next_symbol in self.assets.keys():
                            if next_coin['quote']['USD']['market_cap'] > (1 - self.params['wiggle']) * coin['quote']['USD']['market_cap']:
                                skipped = symbol
                                symbol = next_symbol
                            break
                weights[symbol] = self.fraction
                lots_open -= 1
                banned_coins.append(symbol)
        self.weights = weights
        for weight in weights:
            weights[weight] = weights[weight]*self.fiat_total
        self.balanced_fiat = weights
        return weights

    def generate_instructions(self):
        # return false if cant trade due to staked
        diff = self.diff_matrix
        instructions = []
        token_diff = self.get_token_diff().transpose()
        new_coins = {}
        gains = self.gains
        # checking for any fiat holdings
        fiat_holdings = self.assets.get(self.params['base_fiat'], False)
        if fiat_holdings:
            usd_amt = fiat_holdings['tot']
        else:
            usd_amt = 0

        for element in diff:
            if element == self.params['base_fiat']:
                continue
            # new coins
            if element not in self.assets.keys():
                new_coins[element] = 0
            # SELLING
            else:
                liquid = (self.assets[element]['tot'] -
                          self.assets[element]['locked'])*self.assets[element]['new_price']
                # take profit
                if gains[element] > self.params['profit_pct'] and liquid > self.params['min_trade_fiat'] and diff[element] > self.params['min_trade_fiat']:
                    instructions.append(
                        {'symbol': element, 'coins': round(float(token_diff[element][0]), 2), 'usd_amt': diff[element], 'side': "SELL"})
                    usd_amt += diff[element]
                    continue
                # dropped coins
                if self.diff_matrix[element] > self.assets[element]['tot']*self.assets[element]['new_price']*0.9 and liquid > 10:
                    instructions.append(
                        {'symbol': element, 'coins': round(float(token_diff[element][0]), 2), 'usd_amt': diff[element], 'side': "SELL"})
                    usd_amt += diff[element]
        # check usd amount before doing buys
        if usd_amt < self.params['abs_min_fiat']:
            return False

        # prio 1: handpicks
        for symbol in self.params['hard_hp']:
            diff = -self.diff_matrix[symbol]
            if diff > self.params['min_trade_fiat'] and diff < usd_amt:
                instructions.append({'symbol': symbol, 'coins': round(
                    float(token_diff[symbol][0]), 2), 'usd_amt': diff, 'side': "BUY"})
                usd_amt -= diff
            elif diff > usd_amt:
                instructions.append({'symbol': symbol, 'coins': round(
                    usd_amt/self.assets[symbol]['new_price']), 'usd_amt': usd_amt, 'side': "BUY"})
                return instructions
        # getting prices for new coins

        diff_m = self.diff_matrix
        for element in self.market_data:
            if element['symbol'] in new_coins.keys():
                diff_fiat = diff_m[element['symbol']]
                price = element['quote']['USD']['price']
                new_coins[element['symbol']] = [round(
                    float(diff_fiat/price)*-1, 4), price]

        # prio 3: mcap_coins that we have
        mcap_diffs = {}
        for element in self.diff_matrix:
            if element not in self.params['hard_hp']:
                mcap_diffs[element] = self.diff_matrix[element]
            # sort mcaps
        mcap_diffs = sorted(mcap_diffs.items(), key=lambda x: x[1])
        # get list of all mcap diffs that we are missing and are viable
        mcap_diffs = list(
            filter(lambda x: x[1] < -self.params['min_trade_fiat'], mcap_diffs))

        lots = math.floor(usd_amt/self.params['abs_min_fiat'])
        if lots > len(mcap_diffs):
            lots = len(mcap_diffs)
        tot = 0
        for i in range(lots):
            try:
                coins = round((usd_amt/lots) /
                              self.assets[mcap_diffs[i][0]]['new_price'], 3)
            except (KeyError):
                price = 0
                market_data = self.market_data
                for item in market_data:

                    if item['symbol'] == mcap_diffs[i][0]:
                        price = item['quote']['USD']['price']
                coins = round((usd_amt/lots)/price, 3)
            instructions.append({
                'symbol': mcap_diffs[i][0],
                'coins': coins,
                'usd_amt': usd_amt/lots,
                'side': "BUY"
            }
            )

            tot += usd_amt/lots
        usd_amt -= tot

        mcap_diffs = dict(mcap_diffs)
        for element in mcap_diffs:
            diff_fiat = mcap_diffs[element] * -1
            if diff_fiat < self.params['min_trade_fiat'] or usd_amt < self.params['min_trade_fiat']:
                return instructions
            if usd_amt < diff_fiat:
                instructions.append(
                    {'symbol': element, 'coins': round(usd_amt/self.assets[element]['new_price'], 3), 'usd_amt': usd_amt, 'side': "BUY"})
                return instructions
            instructions.append(
                {'symbol': element, 'coins': -1 * round(float(token_diff[element][0]), 2), 'usd_amt': diff_fiat, 'side': "BUY"})
            usd_amt -= diff_fiat
        return instructions

    def instruct(self):
        # free usd to trade for?
        if self.assets.get(self.params['base_fiat'], {}).get('tot', 0) > self.params['abs_min_fiat']:
            return self.generate_instructions()
        # take profit?
        for symbol in self.gains:
            if self.gains[symbol] > self.params['profit_pct'] and self.diff_matrix[symbol] > self.params['min_trade_fiat']:
                return self.generate_instructions()
        # dropped coins?
        for element in self.assets:
            difference = self.diff_matrix[element]
            holding = self.assets[element]['tot'] * \
                self.assets[element]['new_price']*self.params['wiggle']
            if difference > holding:
                return self.generate_instructions()
        return False

    def get_gains(self):
        return self.gains

    def get_fiat_total(self):
        return self.fiat_total
