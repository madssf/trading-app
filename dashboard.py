import streamlit as st
import pandas as pd
import backend
import lambda_func
import models


import plotly.graph_objects as go
from plotly import tools
import plotly.offline as py
import plotly.express as px
# getting backend data
sheet_names = ["curr_pf", "model_inputs", "staked", "deposits"]
#               "watchlist", "deposits", "trade_log", "order_log"]


sheets = backend.get_sheets(sheet_names)
assets = backend.get_assets()
cmc_market_data = backend.cmc_market_data()
model = models.FundamentalsRebalancingStakingHODL(
    assets, sheets['model_inputs'], cmc_market_data)

instructions = model.instruct()
deposited = 0
for amt in sheets['deposits']['USD']:
    deposited += amt

st.sidebar.title('options')
st.sidebar.subheader('assets')
st.sidebar.write(f"fiat value: {round(model.fiat_total)} USD")
st.sidebar.write(f"deposited: {round(deposited)} USD")
st.sidebar.write(
    f"performance: {round(((model.fiat_total-deposited)/deposited)*100,2)}%")
st.sidebar.write(f"mcap_coins: {model.mcap_coins}")
invoke = st.sidebar.button("invoke lambda function")
if invoke:
    lambda_func.lambda_handler(
        {"source": "dashboard"}, {'asssets': assets, 'inputs': sheets['model_inputs'], 'market_data': cmc_market_data})
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
fig = px.pie(pf_df.transpose(), values='value', names=names, hole=.3)
fig.update_traces(textposition='inside',
                  textinfo="label + percent")
st.plotly_chart(fig)
diff_df = pd.DataFrame(model.get_diff_matrix(), index=[1]).transpose()
fig = px.bar(diff_df)
st.plotly_chart(fig)


diffs = model.token_diff()
gains = pd.DataFrame(model.get_gains(), index=[
                     0]).transpose()
gains.columns = ['% change']
diffs['% change'] = gains.astype(float)*100
diffs['avg_price'] = assets_df['avg_price'].astype(float)
diffs['new_price'] = assets_df['new_price'].astype(float)

st.write(diffs)

st.write('model_inputs')
st.write(sheets["model_inputs"].transpose())
st.write('staked')
st.write(sheets["staked"])
# st.write('trade_log')
# st.write(sheets["trade_log"])
# st.write('order_log')
# st.write(sheets["order_log"])
st.write('deposits')
st.write(sheets["deposits"])
