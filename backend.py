import json
import pygsheets
from google.oauth2 import service_account
from binance.client import Client
from requests import Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects

import config
import streamlit as st
from copy import copy

cmc_url_base = "https://pro-api.coinmarketcap.com/v1/"
quotes_latest = "cryptocurrency/quotes/latest"
listings_latest = "cryptocurrency/listings/latest"


cmc_headers = {
    'Accepts': 'application/json',
    'X-CMC_PRO_API_KEY': config.CMC_KEY,
}

cmc_session = Session()
cmc_session.headers.update(cmc_headers)


@st.cache
def cmc_quotes_latest(symbols):
    '''
    :symbols: list[string]
    '''
    # convert list to commaseparated string before putting in payload
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
        return(data)
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        return(e)


@st.cache
def cmc_market_data():
    try:
        response = cmc_session.get(cmc_url_base+listings_latest)
        data = json.loads(response.text)
        if "data" not in data.keys():
            raise ValueError(f"data not in cmc-request: {data}")
        return(data)

    except (ConnectionError, Timeout, TooManyRedirects) as e:
        return(e)


@st.cache
def get_sheet_by_name(name):
    with open('sheets_config.json') as source:
        info = json.load(source)

    credentials = service_account.Credentials.from_service_account_info(info)

    client = pygsheets.authorize(service_account_file='sheets_config.json')

    spreadsheet_url = "https://docs.google.com/spreadsheets/d/1ckQ3JaGAsowqNDCp_DrqQxqfvpPrFvY3TpYrtewrwEE/edit?usp=sharing"
    sheet_data = client.sheet.get(
        '1ckQ3JaGAsowqNDCp_DrqQxqfvpPrFvY3TpYrtewrwEE')

    sheet = client.open_by_key('1ckQ3JaGAsowqNDCp_DrqQxqfvpPrFvY3TpYrtewrwEE')
    return sheet.worksheet_by_title(name).get_as_df()


@st.cache
def get_sheets(names):
    return {name: get_sheet_by_name(name) for name in names}


@st.cache
def get_assets():
    '''
    :returns: {coins: {tot, flex, locked, avg_price, new_price, stake_exp}}}
    '''
    data = {}
    temp = {'tot': 0, 'flex': 0, 'locked': 0,
            'avg_price': 0, 'new_price': 0, 'stake_exp': -1}
    # get binance api account
    client = Client(config.BINANCE_API_KEY, config.BINANCE_SECRET_KEY)
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
            data[symbol] = data.get(symbol, copy(temp))
            data[symbol]['tot'] += amt
            if locked:
                data[symbol]['locked'] += amt
            if flexed:
                data[symbol]['flex'] += amt
    staked = get_sheet_by_name("staked").transpose()
    for symbol in staked:
        coin = staked[symbol]
        if coin['symbol'] not in data.keys():
            data[coin['symbol']] = temp
            data[coin['symbol']]['locked'] = coin['amount']
        else:
            data[coin['symbol']]['locked'] += coin['amount']
        data[coin['symbol']]['tot'] += coin['amount']
        data[coin['symbol']]['stake_exp'] = staked[symbol]['stake_exp']
    curr_pf = get_sheet_by_name("curr_pf").transpose()
    avgs = {}
    for item in curr_pf:
        avgs[curr_pf[item]['symbol']] = curr_pf[item]['avg_price']
    for item in avgs.keys():

        data[item]['avg_price'] = float(avgs[item])

    quotes = cmc_quotes_latest([x for x in data.keys()])['data']
    for symbol in data:
        data[symbol]['new_price'] = quotes[symbol]['quote']['USD']['price']

    return data


def place_order(trade):
    print(f"place order not implemented: {trade}")
    return
