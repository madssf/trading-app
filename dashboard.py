import streamlit as st
import pandas as pd
import backend
import lambda_func
import models
from datetime import datetime

import plotly.graph_objects as go
from plotly import tools
import plotly.offline as py
import plotly.express as px
# getting backend and model instructions
# "watchlist", "deposits", "trade_log", "order_log"
sheet_names = ["curr_pf", "model_inputs", "staked", "deposits"]
sheets = backend.get_sheets(sheet_names)
assets = backend.get_assets()
cmc_market_data = backend.cmc_market_data()
model = models.FundamentalsRebalancingStakingHODL(
    assets, sheets['model_inputs'], cmc_market_data)

instructions = model.instruct()

# calculating display information
deposited = 0
for data in cmc_market_data:
    if data['symbol'] == 'BTC':
        btc_price = data['quote']['USD']['price']
        break
btc_avg = 0
deposits = sheets['deposits'].transpose()
for item in deposits:
    deposited += deposits[item]['USD']
    btc_avg += deposits[item]['USD']*deposits[item]['BTC/USD']
btc_avg = btc_avg/deposited
perf = round(((model.fiat_total-deposited)/deposited)*100, 2)
btc_perf = round(100*(btc_price-btc_avg)/btc_avg, 2)
now = datetime.now().strftime("%H:%M:%S")
st.sidebar.write(f'last updated **{now}**')
st.sidebar.header(f"{round(model.get_fiat_total())} USD")
st.sidebar.write(f"performance ** {perf} % **")
st.sidebar.write(f"btc perf ** {btc_perf} % **")
st.sidebar.write(f"diff ** {round(perf - btc_perf, 2)} % **")
st.sidebar.subheader('model')
st.sidebar.write(f"mcap_coins **{model.mcap_coins}**")
st.sidebar.write(f"dynamic_mcap **{model.dynamic_mcap}**")

invoke = st.sidebar.button("invoke lambda function")
if invoke:
    event = {"source": "dashboard"}
    context = cmc_market_data
    lambda_func.lambda_handler(event, context)
    invoke = False


st.header('dashboard')
st.subheader('assets')
if instructions:
    st.sidebar.write("trade condition detected")
    st.sidebar.write(instructions)

assets_df = pd.DataFrame(assets).transpose()
fiat_assets = assets_df['tot']*assets_df['new_price']
pf_df = pd.DataFrame(fiat_assets)
pf_df.columns = ['value']
pf_df = pf_df.transpose()
names = []
for element in pf_df.keys():
    names.append(element)
pf_fig = px.pie(pf_df.transpose(), values='value', names=names, hole=.3)
pf_fig.update_traces(textposition='inside',
                     textinfo="label + percent")
st.plotly_chart(pf_fig)

diff_df = pd.DataFrame(model.get_diff_matrix(), index=[1]).transpose()
fig = px.bar(diff_df)
st.plotly_chart(fig)


pf = model.token_diff()

gains = pd.DataFrame(model.get_gains(), index=[
    0]).transpose()
# gains.columns = ['% change']
pf['% change'] = gains.astype(float)*100
fiat_diffs = {}
diff_m = model.get_diff_matrix()
for element in diff_m:
    if element in pf.index.values:
        fiat_diffs[element] = diff_m[element]
pf['fiat_diff'] = fiat_diffs.values()
pf['avg_price'] = assets_df['avg_price'].astype(float)
pf['new_price'] = assets_df['new_price'].astype(float)
pf_market = backend.cmc_quotes_latest(pf.transpose().keys())
market_df = {}
for element in pf_market:
    market_df[element] = pf_market[element]['quote']['USD']
market_df = pd.DataFrame(market_df).transpose().drop(
    columns=['last_updated', 'market_cap', 'price', 'volume_24h'])
market_df = market_df.apply(pd.to_numeric)
market_df.columns = ["%1h", "%24h", "%7d", "%30d", "%60d", "%90d"]
# daily % change, total dollar value, total tokens here
st.subheader('portfolio details')
st.write(pf)
st.write(market_df)

st.subheader('model_inputs')
model_inputs_df = sheets["model_inputs"].transpose()
model_inputs_df.columns = ['parameter']
st.write(model_inputs_df)
bal_pf = pd.DataFrame(model.balanced_fiat, index=['value'])
bal_fig = px.pie(bal_pf.transpose(), values='value',
                 names=bal_pf.keys(), hole=.3)
bal_fig.update_traces(textposition='inside',
                      textinfo="label + percent")
st.write("balanced portfolio")
st.plotly_chart(bal_fig)
st.subheader('staked')
st.write(sheets["staked"])
# st.write('trade_log')
# st.write(sheets["trade_log"])
# st.write('order_log')
# st.write(sheets["order_log"])
st.subheader('deposits')
st.write(f"deposited: {round(deposited)} USD")

st.write(sheets["deposits"].drop(columns=['FEES', 'USD/NOK',
         'ETH/USD', 'ETH', 'BNB', 'BNB/USD', 'CRYPTO', 'BTC', 'BTC/USD', 'NOK']))
