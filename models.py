from backend import cmc_market_data
import pandas as pd
import math
from abc import ABC, abstractmethod


class Model(ABC):

    # return list of valid trades to perform if trade condition met
    @abstractmethod
    def instruct():
        # check difference against params to determine whether to rebalance
        return


class FundamentalsRebalancingStakingHODL(Model):

    def __init__(self, assets, params, market_data):
        self.assets = assets
        self.params = params
        self.market_data = market_data
        self.hard_hp = self.params['handpicked_symbols'][0]
        self.hard_hp_amts = self.params['handpicked_amts'][0]
        if "," in self.hard_hp:
            self.hard_hp = self.hard_hp.split(',')
            self.hard_hp_amts = [float(x)
                                 for x in self.hard_hp_amts.split(',')]
        else:
            self.hard_hp = [self.hard_hp]
            self.hard_hp_amts = [self.hard_hp_amts]

        gains = {}
        for symbol in self.assets:
            try:
                gains[symbol] = (self.assets[symbol]['new_price']-self.assets[symbol]
                                 ['avg_price']) / self.assets[symbol]['avg_price']
            except(ZeroDivisionError):
                gains[symbol] = 0
        self.gains = gains
        fiat_temp = 0
        for asset in assets:
            fiat_temp += assets[asset]['new_price'] * assets[asset]['tot']
        self.fiat_total = fiat_temp

        self.balanced_pf = self.balanced_portfolio()
        self.get_diff_matrix()

    def token_diff(self):
        data = {}

        for element in self.diff_matrix:
            if element not in self.assets.keys():
                pass
            else:
                data[element] = self.diff_matrix[element] / \
                    self.assets[element]['new_price']

        data = pd.DataFrame(data, index=[0]).transpose()
        data.columns = ['token diff']
        return data

    def get_diff_matrix(self):
        # do some calculatons with input_params
        balanced = self.balanced_pf
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
        self.diff_matrix = diffs
        return diffs

    def balanced_portfolio(self):
        weights = {}
        banned_coins = self.params['banned_coins'][0].split(',')
        total = 1
        # handpicked-hard
        hard_hp = self.hard_hp
        hard_hp_amts = self.hard_hp_amts
        for i in range(len(hard_hp)):
            banned_coins.append(hard_hp[i])
            total -= hard_hp_amts[i]
            weights[hard_hp[i].strip()] = float(hard_hp_amts[i])

        min_profit = float(self.params['profit_pct'])
        min_trade_fiat = float(self.params['min_trade_fiat'])
        self.dynamic_mcap = math.floor(
            (min_profit * self.fiat_total * total)/min_trade_fiat)
        mcap_coins = min(max(
            int(self.params['min_mcap_coins'][0]), self.dynamic_mcap), int(self.params['max_mcap_coins'][0]))
        self.mcap_coins = mcap_coins
        self.fraction = total/mcap_coins
        lots_open = self.mcap_coins
        if self.params['handpicked_mcap'][0]:
            symbols = self.params['handpicked_mcap'][0].split(',')
            for symbol in symbols:
                weights[symbol] = self.fraction
                banned_coins.append(symbol)
                lots_open -= 1

        checked = []
        for coin in self.market_data:
            symbol = coin['symbol']
            mcapsize = coin['quote']['USD']['market_cap']
            if lots_open < 1:
                break
            if symbol not in banned_coins:
                # missing coin, see if we have an almost as good coin already
                if symbol not in self.assets.keys():
                    for next_coin in self.market_data:
                        next_symbol = next_coin['symbol']
                        if next_symbol not in checked and next_symbol not in banned_coins and next_symbol != symbol and next_symbol in self.assets.keys():
                            if next_coin['quote']['USD']['market_cap'] > 1-self.params['wiggle'][0] * mcapsize:
                                symbol = next_symbol
                                break
                weights[symbol] = self.fraction
                lots_open -= 1
            checked.append(symbol)
        self.weights = weights
        for weight in weights:
            weights[weight] = weights[weight]*self.fiat_total
        self.balanced_fiat = weights
        return weights

    def generate_instructions(self):
        # return false if cant trade due to staked
        diff = self.diff_matrix
        instructions = []
        token_diff = self.token_diff().transpose()
        new_coins = {}
        gains = self.gains
        # checking for any fiat holdings
        base_fiat = self.params['base_fiat'][0]
        fiat_holdings = self.assets.get(base_fiat, False)
        if fiat_holdings:
            usd_amt = fiat_holdings['tot']
        else:
            usd_amt = 0

        for element in diff:
            # new coins
            if element not in self.assets.keys():
                new_coins[element] = 0
            # SELLING
            else:
                liquid = (self.assets[element]['tot'] -
                          self.assets[element]['locked'])*self.assets[element]['new_price']
                min_fiat_trade = self.params['min_trade_fiat'][0]
                # take profit
                if gains[element] > self.params['profit_pct'][0] and liquid > min_fiat_trade and diff[element] > min_fiat_trade:
                    instructions.append(
                        {'symbol': element, 'coins': round(float(token_diff[element][0]), 2), 'usd_amt': diff[element], 'side': "SELL"})
                    usd_amt += diff[element]
                    continue
                # dropped coins
                if self.diff_matrix[element] > self.assets[element]['tot']*self.assets[element]['new_price']*0.9 and liquid > min_fiat_trade:
                    instructions.append(
                        {'symbol': element, 'coins': round(float(token_diff[element][0]), 2), 'usd_amt': diff[element], 'side': "SELL"})
                    usd_amt += diff[element]
        # check usd amount before doing buys
        if usd_amt < min_fiat_trade:
            return False

        # prio 1: handpicks
        for symbol in self.hard_hp:
            diff = -self.diff_matrix[symbol]
            if diff > min_fiat_trade and diff < usd_amt:
                instructions.append({'symbol': symbol, 'coins': round(
                    float(token_diff[symbol][0]), 2), 'usd_amt': diff, 'side': "BUY"})
                usd_amt += diff
            elif diff > usd_amt:
                instructions.append({'symbol': symbol, 'coins': round(
                    usd_amt/self.assets[symbol]['new_price']), 'usd_amt': usd_amt, 'side': "BUY"})
                return instructions
        # prio 2: coins that we don't currently have but need
        diff_m = self.diff_matrix
        for element in self.market_data:
            if element['symbol'] in new_coins.keys():
                diff_fiat = diff_m[element['symbol']]
                price = element['quote']['USD']['price']
                new_coins[element['symbol']] = [round(
                    float(diff_fiat/price)*-1, 4), price]
        for element in new_coins:
            diff_fiat = diff_m[element] * -1
            if diff_fiat < min_fiat_trade or usd_amt < min_fiat_trade:
                return instructions
            if usd_amt < diff_fiat:
                instructions.append(
                    {'symbol': element, 'coins': round(usd_amt/new_coins[element][1], 3), 'usd_amt': usd_amt, 'side': "BUY"})
                return instructions
            instructions.append(
                {'symbol': element, 'coins': new_coins[element][0], 'usd_amt': diff_fiat, 'side': "BUY"})
            usd_amt -= diff_fiat
        # prio 3: mcap_coins that we have
        mcap_diffs = {}
        for element in self.diff_matrix:
            if element not in new_coins.keys() and element not in self.hard_hp:
                mcap_diffs[element] = self.diff_matrix[element]
            # sort mcaps
        mcap_diffs = sorted(mcap_diffs.items(), key=lambda x: x[1])
        # get list of all mcap diffs that we are missing and are viable
        mcap_diffs = list(filter(lambda x: x[1] < -min_fiat_trade, mcap_diffs))
        lots = math.floor(usd_amt/min_fiat_trade)
        if lots > len(mcap_diffs):
            lots = len(mcap_diffs)
        tot = 0
        for i in range(lots):
            instructions.append({
                'symbol': mcap_diffs[i][0],
                'coins': round((usd_amt/lots)/self.assets[mcap_diffs[i][0]]['new_price'], 3),
                'usd_amt': usd_amt/lots,
                'side': "BUY"
            }
            )
            tot += usd_amt/lots
        usd_amt -= tot

        mcap_diffs = dict(mcap_diffs)
        for element in mcap_diffs:
            diff_fiat = mcap_diffs[element] * -1
            if diff_fiat < min_fiat_trade or usd_amt < min_fiat_trade:
                return instructions
            if usd_amt < diff_fiat:
                instructions.append(
                    {'symbol': element, 'coins': round(usd_amt/self.assets[element]['new_price'], 3), 'usd_amt': usd_amt, 'side': "BUY"})
                return instructions
            instructions.append(
                {'symbol': element, 'coins': -1 * round(float(token_diff[element][0]), 2), 'usd_amt': diff_fiat, 'side': "BUY"})
            usd_amt -= diff_fiat
        return instructions

    # checking if gain on any coin > rules['profit_pct'] or if free usd to trade for
    def instruct(self):
        if self.fiat_total > self.params['min_trade_fiat'][0]:
            return self.generate_instructions()
        for symbol in self.gains:
            if self.gains[symbol] > self.params['profit_pct'][0] and self.diff_matrix[symbol] > self.params['min_trade_fiat'][0]:
                return self.generate_instructions()
        return False

    def get_gains(self):
        return self.gains

    def get_fiat_total(self):
        return self.fiat_total
