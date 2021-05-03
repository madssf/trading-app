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
        self.gains = None

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
        balanced = self.balanced_portfolio(
            self.assets, self.params, self.market_data)
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

    def balanced_portfolio(self, assets, params, market_data):
        self.fiat_total = 0
        weights = {}
        banned_coins = params['banned_coins'][0].split(',')
        for asset in assets:
            self.fiat_total += assets[asset]['new_price'] * \
                assets[asset]['tot']
        total = 1
        # handpicked-hard
        if params['handpicked_1'][0]:
            symbol = params['handpicked_1'][0].split(',')[0]
            banned_coins.append(symbol)
            amt = float(params['handpicked_1'][0].split(',')[1])
            weights[symbol] = float(amt)
            total -= amt
        if params['handpicked_2'][0]:
            amt = 0
            symbol = params['handpicked_2'][0].split(',')[0]
            banned_coins.append(symbol)
            amt = float(params['handpicked_2'][0].split(',')[1])
            weights[symbol] = float(amt)
            total -= amt
        if params['handpicked_3'][0]:
            amt = 0
            symbol = params['handpicked_3'][0].split(',')[0]
            banned_coins.append(symbol)
            amt = float(params['handpicked_3'][0].split(',')[1])
            weights[symbol] = float(amt)
            total -= amt
        min_profit = float(params['profit_pct'])
        min_trade_fiat = float(params['min_trade_fiat'])
        dynamic_mcap = math.floor(
            (min_profit * self.fiat_total * total)/min_trade_fiat)

        mcap_coins = max(int(params['min_mcap_coins'][0]), dynamic_mcap)
        self.mcap_coins = mcap_coins
        fraction = total/mcap_coins
        if params['handpicked_mcap'][0]:
            symbols = params['handpicked_mcap'][0].split(',')
            for symbol in symbols:
                weights[symbol] = fraction
                banned_coins.append(symbol)
                mcap_coins -= 1
        for coin in market_data['data']:
            symbol = coin['symbol']
            if mcap_coins < 1:
                break
            if symbol not in banned_coins:
                weights[symbol] = fraction
                mcap_coins -= 1
        self.weights = weights
        for weight in weights:
            weights[weight] = weights[weight]*self.fiat_total
        self.balanced_fiat = weights
        return weights

    def generate_instructions(self):
        # return false if cant trade due to staked
        diff = self.get_diff_matrix()
        # use diff matrix to generate instructions
        # adjusting for locked staking
        data = []

        for element in diff:
            # deal with selling first
            try:

                if diff[element] > self.params['min_trade_fiat'][0]:

                    liquid = self.assets[element]['tot'] - \
                        self.assets[element]['locked']
                    if liquid > self.params['min_trade_fiat'][0]:
                        if diff[element] > 0:
                            type = 'sell'
                        else:
                            type = 'buy'
                        data.append([element, diff[element], type])
                    else:
                        data.append(
                            [element, diff[element], "sell - wait for unstake"])
            except(KeyError):
                data.append([element], diff[element])
        return data

    # checking if gain on any coin > rules['profit_pct']
    def instruct(self):
        gains = {}
        for symbol in self.assets:
            try:
                gains[symbol] = (self.assets[symbol]['new_price']-self.assets[symbol]
                                 ['avg_price']) / self.assets[symbol]['avg_price']
            except(ZeroDivisionError):
                gains[symbol] = 0
        self.gains = gains
        for symbol in gains:
            if gains[symbol] > self.params['profit_pct'][0]:
                return self.generate_instructions()
        return None

    def get_gains(self):
        return self.gains
