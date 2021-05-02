import pandas as pd
from abc import ABC, abstractmethod


class Model(ABC):

    # return list of valid trades to perform if trade condition met
    @abstractmethod
    def trade_condition():
        # check difference against params to determine whether to rebalance
        return


class FundamentalsRebalancingStakingHODL(Model):

    # overriding abstract method
    def get_optimal_portfolio(rules):
        # do some calculatons with input_params
        # return optimal portfolio
        return

    def trade_condition(self, assets, prices, rules):
        valid_trades = None
        return valid_trades
