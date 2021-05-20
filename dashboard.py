import streamlit as st
import pandas as pd
import backend
import lambda_func
import models
from datetime import datetime
import pytz
import plotly.express as px
from graphs import graphs

# getting backend and model instructions
sheet_names = ["curr_pf", "model_inputs", "staked",
               "deposits", "invoke_log", 'assets_log', 'mcap_log']

sheets = backend.get_sheets(sheet_names)

assets = backend.get_assets()
cmc_market_data = backend.cmc_market_data()
now = datetime.now(pytz.timezone(st.secrets["TIMEZONE"])).strftime("%H:%M:%S")
model = models.McapModel(
    assets, sheets['model_inputs'], cmc_market_data)


token_hist, hist_fig = graphs.PFHistory(
    sheets['assets_log'])
perf_stats, perf_fig = graphs.PerfHistory(sheets['mcap_log'], token_hist)


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
day_intervals = [1, 7, 30]
perf_matrix = {x: {} for x in perf_stats.columns}
for pf_type in perf_stats.columns:
    for num_days in day_intervals:
        perf_matrix[pf_type][num_days] = f"{round((perf_stats[pf_type].iloc[-1] - perf_stats[pf_type].iloc[-(num_days+1)])*100,2)} %"
st.sidebar.table(perf_matrix)
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


pf_fig = graphs.PFPIE(assets)
st.subheader('portfolio')
st.plotly_chart(pf_fig)


# diff bar chart

diff_df, rb_fig = graphs.RBDiff(model.diff_matrix, model.get_token_diff())
st.subheader('rebalancing')
st.plotly_chart(rb_fig)


# perf history graph
st.subheader('performance history')
st.plotly_chart(perf_fig)

# performance and market data
market_df = graphs.MarketDF(model.get_gains(), assets, diff_df)
st.write(market_df)

# history
st.subheader('portfolio history')
st.plotly_chart(hist_fig)

# staked, coin holdings
assets_df = pd.DataFrame(assets).transpose()
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
