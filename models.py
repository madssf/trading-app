from pandas.core import base
from backend import cmc_market_data
import pandas as pd
import math
from abc import ABC, abstractmethod
import copy


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
    # overriding abstract method

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
        data = {}
        for element in balanced:
            try:
                data[element] = (self.assets[element]['tot']*self.assets[element]
                                 ['new_price']) - balanced[element]
            except(KeyError) as e:
                data[element] = -balanced[element]
        for element in self.assets:
            if element not in data.keys():
                data[element] = self.assets[element]['tot'] * \
                    self.assets[element]['new_price']
        self.diff_matrix = data
        return data

    def balanced_portfolio(self):
        weights = {}
        banned_coins = self.params['banned_coins'][0].split(',')
        total = 1
        # handpicked-hard
        if self.params['handpicked_1'][0]:
            symbol = self.params['handpicked_1'][0].split(',')[0]
            banned_coins.append(symbol)
            amt = float(self.params['handpicked_1'][0].split(',')[1])
            weights[symbol] = float(amt)
            total -= amt
        if self.params['handpicked_2'][0]:
            amt = 0
            symbol = self.params['handpicked_2'][0].split(',')[0]
            banned_coins.append(symbol)
            amt = float(self.params['handpicked_2'][0].split(',')[1])
            weights[symbol] = float(amt)
            total -= amt
        if self.params['handpicked_3'][0]:
            amt = 0
            symbol = self.params['handpicked_3'][0].split(',')[0]
            banned_coins.append(symbol)
            amt = float(self.params['handpicked_3'][0].split(',')[1])
            weights[symbol] = float(amt)
            total -= amt
        min_profit = float(self.params['profit_pct'])
        min_trade_fiat = float(self.params['min_trade_fiat'])
        self.dynamic_mcap = math.floor(
            (min_profit * self.fiat_total * total)/min_trade_fiat)
        mcap_coins = max(
            int(self.params['min_mcap_coins'][0]), self.dynamic_mcap)
        self.mcap_coins = mcap_coins
        self.fraction = total/mcap_coins
        lots_open = self.mcap_coins
        if self.params['handpicked_mcap'][0]:
            symbols = self.params['handpicked_mcap'][0].split(',')
            for symbol in symbols:
                weights[symbol] = self.fraction
                banned_coins.append(symbol)
                lots_open -= 1
        for coin in self.market_data['data']:
            symbol = coin['symbol']
            if lots_open < 1:
                break
            if symbol not in banned_coins:
                weights[symbol] = self.fraction
                lots_open -= 1
        self.weights = weights
        for weight in weights:
            weights[weight] = weights[weight]*self.fiat_total
        self.balanced_fiat = weights
        return weights

    def generate_instructions(self):
        # return false if cant trade due to staked
        diff = self.get_diff_matrix()
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
                liquid = self.assets[element]['tot'] - \
                    self.assets[element]['locked']
                min_fiat_trade = self.params['min_trade_fiat'][0]
                # take profit
                if gains[element] > self.params['profit_pct'][0] and liquid > min_fiat_trade and diff[element] > min_fiat_trade:
                    instructions.append(
                        {'symbol': element, 'coins': round(float(token_diff[element][0]), 2), 'usd_amt': diff[element], 'side': "SELL"})
                    usd_amt += diff[element]
                # dropped coins
                if self.diff_matrix[element] > self.assets[element]['tot']*0.9 and liquid > min_fiat_trade:
                    instructions.append(
                        {'symbol': element, 'coins': round(float(token_diff[element][0]), 2), 'usd_amt': diff[element], 'side': "SELL"})
                    usd_amt += diff[element]

        # check usd amount doing buys
        if usd_amt < min_fiat_trade:
            return False

        # coins that we don't currently have but need
        for element in self.market_data['data']:
            if element['symbol'] in new_coins.keys():
                diff_fiat = diff[element['symbol']]
                price = element['quote']['USD']['price']
                new_coins[element['symbol']] = [round(
                    float(diff_fiat/price)*-1, 4), price]
        for element in new_coins:
            diff_fiat = diff[element] * -1
            if usd_amt < min_fiat_trade:
                break
            if usd_amt < diff_fiat:
                instructions.append(
                    {'symbol': element, 'coins': usd_amt/new_coins[element][1], 'usd_amt': usd_amt, 'side': "BUY"})
                usd_amt = 0
                break
            instructions.append(
                {'symbol': element, 'coins': new_coins[element][0], 'usd_amt': diff_fiat, 'side': "BUY"})
            usd_amt -= diff_fiat

        return instructions

    # checking if gain on any coin > rules['profit_pct']
    def instruct(self):
        for symbol in self.gains:
            if self.gains[symbol] > self.params['profit_pct'][0]:
                return self.generate_instructions()
        return False

    def get_gains(self):
        return self.gains

    def get_fiat_total(self):
        return self.fiat_total
