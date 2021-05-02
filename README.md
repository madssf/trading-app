# trading-app

source /Users/mads/.pyenv/versions/trading-app/bin/activate

## Installation - Start here!

- clone the project
- recommended: set up a virtual environment
- install requirements:
  `pip install -r requirements.txt`
- make a file called config.py - use config_template.py

## dashboard.py

streamlit run dashboard.py

## monitor

python monitor.py

## How it works

1. Choose a model and set input parameters
2. Wait for the model to signal that a trade condition is met
3. Model generates a list of trades to perform
4. Trades are executed... return to step 2

## Models

All models must implement:

        @abstractmethod
        def get_trade_instructions(portfolio, rules, prices):
          # check portfolio and prices against rules
          # return None if trading condition not met
          # else: return a list of valid trades to perform

### FundamentalsRebalancingStakingHODL

- Holds a portfolio of equal dollar amounts of the highest <em>x</em> coins by market cap, where <em>x</em> is the highest amount of coins allowing take-profit after a set percentage gain, given a minimum trade amount (in fiat currency).

- Can be overriden with handpicked coins

- Any handpicked coins that are not given a set percentage amount will take the place of the automatically included coins from the market portfolio that have the lowest market cap

- Can be overriden to ban certain coins - e.g coins that are only used for payment transactions

- Takes coins locked in staking into account when generating list of trades to perform

- Trading condition: <em>x</em>% price increase from average/starting price
  - set average/starting price equal to current price after buying or selling, keep old value if coin is not involved in rebalancing

#### Input parameters

- `hanpdicked_coins: dict[string symbol: float weight]`

- `minimum_market_coins: int`

- `take_profit_pct: float`

- `min_fiat_trade_amt: int`

- `banned_coins: list[string symbol]`

#### Algorithm

      total_handpicked = x for x in lambda weights where weights

      market_pf_weight = 1 - total_handpicked
      if weight == None:
        weight == market_pf_weight

#### Links

- https://cs.stackexchange.com/questions/80798/portfolio-rebalancing-algorithm
- https://investopedia.com/articles/stocks/11/rebalancing-strategies.asp
- https://en.wikipedia.org/wiki/Metcalfe%27s_law

### MarketCapPortfolio

#### Input parameters

- `minimum_market_coins: int`
- `banned_coins: list[string symbol]`

## Performing trades

- Redeems coins from flexible savings if needed
- Does not stake or set to flexible savings after performing trades
