# TODO:

## Email backend

- stop mail from spamming

## Dashboard functionality

- control scheduler from dashboard
- pefomrance vs btc etc
- get staked apr and do some calc
- show daily % gain and more data on dashboard
- watchlist
- general market analysis, fundamentals

## Simulation

- for testing: change assets

## G sheets integration

- logging to g-sheets
- sorting of staked in g-sheets

## backend

- cache on dashboard but not lambda func
- error handling requests (cmc)
  - passing ['data] from cmc_market_data
- check valid input from g-sheets when constructing models
- handle asset in assets[avg] but not in balanced portfolio
  - sell?

## models.py

- merge model with MCAP model
  - weighted as param True/False

## trade_instructions

- fix buy orders, check available usdt
- handle market crash (resetting avg_prices)

## other

- better readme instructions
