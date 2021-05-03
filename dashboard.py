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

st.sidebar.title('options')
invoke = st.sidebar.button("invoke lambda function")
if invoke:
    lambda_func.lambda_handler(
        {"source": "dashboard"}, {'asssets': assets, 'inputs': sheets['model_inputs'], 'market_data': cmc_market_data})
    invoke = False


st.header('dashboard')
st.subheader('assets')
assets_df = pd.DataFrame(assets).transpose()
# st.write(assets_df)
fiat_assets = assets_df['tot']*assets_df['new_price']
pf_df = pd.DataFrame(fiat_assets)
pf_df.columns = ['value']
pf_df = pf_df.transpose()
# st.write(pf_df.transpose())
names = []
for element in pf_df.keys():
    names.append(element)
fig = px.pie(pf_df.transpose(), values='value', names=names, hole=.3)
fig.update_traces(textposition='inside',
                  textinfo="label + percent")
st.plotly_chart(fig)
model = models.FundamentalsRebalancingStakingHODL(
    assets, sheets['model_inputs'], cmc_market_data)
diff_df = pd.DataFrame(model.get_diff_matrix(), index=[1]).transpose()
fig = px.bar(diff_df)
st.plotly_chart(fig)

st.write(f"fiat value: {model.fiat_total}")
st.write(f"mcap_coins: {model.mcap_coins}")
st.write("trade condition - instructions:")
st.write(model.instruct())
diffs = model.token_diff()
gains = pd.DataFrame(model.get_gains(), index=[
                     0]).transpose()
gains.columns = ['% change']
diffs['% change'] = gains
diffs['avg_price'] = assets_df['avg_price']
diffs['new_price'] = assets_df['new_price']

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
