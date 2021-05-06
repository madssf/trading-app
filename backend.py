import json
import pygsheets
from binance.client import Client
from requests import Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
from google.oauth2 import service_account
import streamlit as st
from copy import copy

service_acc = st.secrets['SERVICE_ACC']
SCOPES = ('https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive')
creds = service_account.Credentials.from_service_account_info(
    service_acc, scopes=SCOPES)
sheets_client = pygsheets.authorize(custom_credentials=creds)
client = Client(st.secrets['BINANCE_API_KEY'],
                st.secrets['BINANCE_SECRET_KEY'])

cmc_url_base = "https://pro-api.coinmarketcap.com/v1/"
quotes_latest = "cryptocurrency/quotes/latest"
listings_latest = "cryptocurrency/listings/latest"


cmc_headers = {
    'Accepts': 'application/json',
    'X-CMC_PRO_API_KEY': st.secrets['CMC_KEY'],
}

cmc_session = Session()
cmc_session.headers.update(cmc_headers)


def cmc_quotes_latest(symbols):
    '''
    :symbols: list[string]
    '''
    symbol_str = ""
    for symbol in symbols:
        if len(symbol_str) < 1:
            symbol_str = symbol
        else:
            symbol_str += f",{symbol}"
    payload = {"symbol": symbol_str}
    try:
        response = cmc_session.get(cmc_url_base+quotes_latest, params=payload)
        data = json.loads(response.text)
        if "data" not in data.keys():
            raise ValueError(f"data not in cmc-request: {data}")
        return(data['data'])
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        return(e)


def cmc_market_data():
    try:
        response = cmc_session.get(cmc_url_base+listings_latest)
        data = json.loads(response.text)
        if "data" not in data.keys():
            raise ValueError(f"data not in cmc-request: {data}")
        return(data['data'])

    except (ConnectionError, Timeout, TooManyRedirects) as e:
        return(e)


def get_sheet_by_name(name):

    sheet = sheets_client.open_by_key(
        st.secrets['SHEETS_ID'])
    return sheet.worksheet_by_title(name).get_as_df()


def get_sheets(names):
    return {name: get_sheet_by_name(name) for name in names}


def write_to_sheet(name, data):
    sheet = sheets_client.open_by_key(
        st.secrets['SHEETS_ID']).worksheet_by_title(name)
    sheet.insert_rows(1, values=list(data))
    return


def get_assets():
    '''
    :returns: dict{coin: {tot, flex, locked, avg_price, new_price, stake_exp}}}
    '''
    assets = {}
    # get binance api account
    balances = client.get_account()['balances']
    for item in balances:
        flexed = False
        locked = False
        amt = float(item['free']) + float(item['locked'])
        if amt > 0:
            symbol = item['asset']
            if symbol[:2] == "LD":
                flexed = True
                symbol = symbol[2:]
            if symbol == "BETH":
                locked = True
                symbol = "ETH"
            if symbol not in assets.keys():
                assets[symbol] = {'tot': 0, 'flex': 0, 'locked': 0,
                                  'avg_price': 0, 'new_price': 0, 'stake_exp': None}

            assets[symbol]['tot'] += amt
            if locked:
                assets[symbol]['locked'] += amt
            if flexed:
                assets[symbol]['flex'] += amt
    # get staked from g-sheets
    staked = get_sheet_by_name("staked")
    for col, coin in staked.iterrows():
        if coin['symbol'] not in assets.keys():
            assets[coin['symbol']] = {'tot': 0, 'flex': 0, 'locked': coin['amount'],
                                      'avg_price': 0, 'new_price': 0, 'stake_exp': None}
        else:
            assets[coin['symbol']]['locked'] += coin['amount']
        assets[coin['symbol']]['tot'] += coin['amount']
        assets[coin['symbol']]['stake_exp'] = coin['stake_exp']
    # get average prices from g-sheets
    current_pf = get_sheet_by_name("curr_pf")
    for col, coin in current_pf.iterrows():
        if coin['symbol'] in assets.keys():
            assets[coin['symbol']]['avg_price'] = float(
                coin['avg_price'])
    quotes = cmc_quotes_latest([x for x in assets.keys()])
    for symbol in assets:
        assets[symbol]['new_price'] = quotes[symbol]['quote']['USD']['price']
    return assets


'''
def place_order(trade):
    print(f"place order not implemented: {trade}")
    return
'''


def get_historical_prices(assets, since, interval=Client.KLINE_INTERVAL_1HOUR):
    data = {}
    for symbol in assets:
        # any stablecoin!
        if symbol == 'USDT' or symbol == "TLM":
            pass
        else:
            data[symbol] = client.get_historical_klines(
                f"{symbol}USDT", interval, since)
    return data
