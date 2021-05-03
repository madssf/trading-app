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
        token_diff = self.token_diff().transpose()
        new_coins = {}
        gains = self.gains
        for element in diff:
            # new coins
            if element not in self.assets.keys():
                new_coins[element] = 0
            # SELLING
            else:
                liquid = self.assets[element]['tot'] - \
                    self.assets[element]['locked']
                min_fiat_trade = self.params['min_trade_fiat'][0]
                if gains[element] > self.params['profit_pct'][0] and liquid > min_fiat_trade and diff[element] > min_fiat_trade:
                    data.append(
                        [element, round(float(token_diff[element][0]), 2), "SELL"])
        # coins that we don't currently have but need
        for element in self.market_data['data']:
            if element['symbol'] in new_coins.keys():
                diff_fiat = diff[element['symbol']] * -1
                price = element['quote']['USD']['price']
                new_coins[element['symbol']] = round(float(diff_fiat/price), 4)

        for element in new_coins:
            data.append([element, new_coins[element], "BUY"])
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
