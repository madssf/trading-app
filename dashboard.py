from pandas.core.algorithms import diff
import streamlit as st
import pandas as pd
import backend
import lambda_func
import models
from datetime import datetime, timedelta
import pytz
import plotly.express as px
from graphs import graphs

# getting backend and model instructions
# "watchlist", "trade_log", "order_log"
sheet_names = ["curr_pf", "model_inputs", "staked",
               "deposits", "invoke_log", 'assets_log', 'mcap_log']

sheets = backend.get_sheets(sheet_names)

assets = backend.get_assets()
cmc_market_data = backend.cmc_market_data()
now = datetime.now(pytz.timezone(st.secrets["TIMEZONE"])).strftime("%H:%M:%S")
model = models.McapModel(
    assets, sheets['model_inputs'], cmc_market_data)


def get_historic_prices(symbols, since):
    return backend.get_historical_prices(symbols, since)


instructions = model.instruct()


# calculating display information
deposited = 0
deposits = sheets['deposits'].transpose()
for item in deposits:
    deposited += deposits[item]['USD']
perf = round(((model.fiat_total-deposited)/deposited)*100, 2)


# SIDEBAR
st.sidebar.subheader('info')
st.sidebar.write(f'updated **{now}**')
st.sidebar.write(f"invoked: **{sheets['invoke_log'].iloc[0][0][11:]}**")
st.sidebar.write(f"balance **{round(model.get_fiat_total())} $**")
st.sidebar.write(f"performance ** {perf} % **")
st.sidebar.subheader('model')
st.sidebar.write(f"mcap_coins **{model.mcap_coins}**")
st.sidebar.write(f"dynamic_mcap **{model.dynamic_mcap}**")
st.sidebar.write(
    f"base trade **{round(model.fiat_total*model.fraction, 2)} $**")
st.sidebar.write(
    f"take profit **{int(sheets['model_inputs']['profit_pct'][0]*100)} %**")
st.sidebar.write(
    f"min trade amt **{sheets['model_inputs']['min_trade_fiat'][0]} $**")
invoke = st.sidebar.button("invoke")
if invoke:
    context = {"source": "dashboard"}
    event = cmc_market_data
    lambda_func.lambda_handler(context, event)
    invoke = False

if instructions:
    st.sidebar.write("trade condition detected")
    st.sidebar.write(instructions)


# DASHBOARD STARTS HERE
assets_df = pd.DataFrame(assets).transpose()


# portfolio pie chart
pf_df = pd.DataFrame(assets_df['tot']*assets_df['new_price'])
pf_df.columns = ['$ amt']
pf_df = pf_df.transpose()
names = []
for element in pf_df.keys():
    names.append(element)
pf_fig = px.pie(pf_df.transpose(), values='$ amt',
                names=names, hole=.3)
pf_fig.update_traces(textposition='inside',
                     textinfo="label + percent")
st.subheader('portfolio')
st.plotly_chart(pf_fig)


# diff bar chart
names = []
for element in pf_df.keys():
    names.append(element)
diff_df = pd.DataFrame(model.get_diff_matrix(), index=['diff']).transpose()
diff_df['tokens'] = model.token_diff()
fig = px.bar(diff_df, hover_data=[
    'tokens'])
fig.update_layout(showlegend=False)
fig.update_yaxes(title='$ diff')
fig.update_xaxes(title='coins')
st.subheader('rebalancing')
st.plotly_chart(fig)


# perf history graph
token_hist, hist_fig = graphs.PFHistory(
    sheets['assets_log'], get_historic_prices)
perf_fig = graphs.PerfHistory(sheets['mcap_log'], token_hist)
st.subheader('performance history')
st.plotly_chart(perf_fig)


# performance and market data
perf_df = pd.DataFrame(model.get_gains(), index=[
    "% gain"]).transpose()
perf_df["% gain"] = perf_df["% gain"].apply(lambda x: float(x)*100)
# getting market data for portfolio coins
pf_market = backend.cmc_quotes_latest(perf_df.transpose().keys())
market_df = {}
for element in pf_market:
    market_df[element] = pf_market[element]['quote']['USD']
market_df = pd.DataFrame(market_df).transpose().drop(
    columns=['last_updated', 'market_cap', 'volume_24h', 'percent_change_30d', 'percent_change_60d', 'percent_change_7d'])
market_df = market_df.apply(pd.to_numeric)
market_df.columns = ["price", "%1h", "%24h", "%90d"]
# daily % change, total dollar value, total tokens here
market_df.insert(loc=1, column='% gain', value=perf_df['% gain'])
market_df.insert(loc=2, column='$ diff', value=diff_df['diff'])
market_df.insert(loc=3, column='avg price', value=assets_df['avg_price'])
st.subheader('market data')
st.write(market_df)

# history
st.subheader('portfolio history')
st.plotly_chart(hist_fig)


# staked, coin holdings
for col in assets_df.columns:
    if col == 'stake_exp':
        assets_df[col] = assets_df[col].apply(
            lambda x: "" if isinstance(x, float) else x)
    else:
        assets_df[col] = assets_df[col].apply(lambda x: round(x, 2))
st.subheader('coin holdings')
st.write(assets_df.drop(columns=['new_price', 'avg_price']))

# model inputs df and balanced df
st.subheader('model inputs')
model_inputs_df = sheets["model_inputs"].transpose()
model_inputs_df.columns = ['parameter']
st.write(model_inputs_df)
bal_pf = pd.DataFrame(model.balanced_fiat, index=['value'])
bal_fig = px.pie(bal_pf.transpose(), values='value',
                 names=bal_pf.keys(), hole=.3)
bal_fig.update_traces(textposition='inside',
                      textinfo="label + percent")
st.subheader("balanced portfolio")
st.plotly_chart(bal_fig)

# deposit log
st.subheader('deposits')
st.write(f"deposited: {round(deposited)} USD")
st.write(sheets["deposits"].drop(columns=['FEES', 'USD/NOK',
         'ETH/USD', 'ETH', 'BNB', 'BNB/USD', 'CRYPTO', 'BTC', 'BTC/USD', 'NOK']))

# invoke log
st.subheader('invoke log')
st.write(sheets['invoke_log'])
