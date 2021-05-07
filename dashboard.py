import streamlit as st
import pandas as pd
import backend
import lambda_func
import models
from datetime import datetime
import pytz
import re
import plotly.express as px

# getting backend and model instructions
# "watchlist", "trade_log", "order_log"
sheet_names = ["curr_pf", "model_inputs", "staked",
               "deposits", "invoke_log", 'assets_log']


sheets = backend.get_sheets(sheet_names)

assets = backend.get_assets()
cmc_market_data = backend.cmc_market_data()
now = datetime.now(pytz.timezone(st.secrets["TIMEZONE"])).strftime("%H:%M:%S")
model = models.FundamentalsRebalancingStakingHODL(
    assets, sheets['model_inputs'], cmc_market_data)


def get_historic_prices(symbols, since):
    return backend.get_historical_prices(symbols, since)


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


# SIDEBAR
st.sidebar.subheader('info')
st.sidebar.write(f'updated **{now}**')
st.sidebar.write(f"balance **{round(model.get_fiat_total())} $**")
st.sidebar.write(f"performance ** {perf} % **")
st.sidebar.write(f"btc perf ** {btc_perf} % **")
st.sidebar.write(f"diff ** {round(perf - btc_perf, 2)} % **")
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
fig = px.bar(diff_df)
fig.update_layout(showlegend=False)
fig.update_yaxes(title='$ diff')
fig.update_xaxes(title='coins')
st.subheader('rebalancing')
st.plotly_chart(fig)

# horizontal diffs
diffs_df = model.token_diff()
st.write(diffs_df.transpose())

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
market_df.insert(loc=2, column='$ diff', value=diff_df)
market_df.insert(loc=3, column='avg price', value=assets_df['avg_price'])
st.subheader('market data')
st.write(market_df)

# history
assets_history = sheets['assets_log']
start = assets_history['time'][len(assets_history)-1]
# get all coins that we have ever held
held = []
for symbols in assets_history['symbols']:
    symbols = symbols.split(',')
    for item in symbols:
        item = re.sub("[^0-9a-zA-Z]", "", item)
        if item not in held:
            held.append(item)
# get binance historical prices for all coins we held:
start = str(int(datetime.timestamp(
    datetime.strptime(start, '%m/%d/%Y, %H:%M:%S'))*1000))

# Open time, Open, High, Low, Close, Volume, Close time, Quote asset volume, Number of trades, Taker buy base asset volume, Taker buy quote asset volume, Ignore.
hist_df = pd.DataFrame(get_historic_prices(held, start)).transpose()
hist_timestamps = [x[6]for x in hist_df.iloc[0]]
assets_timestamps = [int(datetime.timestamp(
    datetime.strptime(x, '%m/%d/%Y, %H:%M:%S'))*1000) for x in assets_history['time']]
assets_df_symbols = [x for x in assets_history['symbols']]
assets_df_tokens = [x for x in assets_history['tokens']]
for i in range(len(assets_df_symbols)):
    assets_df_symbols[i] = assets_df_symbols[i].split(',')
    assets_df_tokens[i] = assets_df_tokens[i].split(',')
    for j in range(len(assets_df_symbols[i])):
        assets_df_symbols[i][j] = re.sub(
            "[^0-9a-zA-Z]", "", assets_df_symbols[i][j])
        assets_df_tokens[i][j] = re.sub(
            "[^0-9a-zA-Z.]", "", assets_df_tokens[i][j])

matches = {}
assets_timestamps.reverse()
for hist_stamp in hist_timestamps:
    closest = None
    for asset_stamp in assets_timestamps:
        if asset_stamp < hist_stamp:
            matches[hist_stamp] = asset_stamp
assets_timestamps.reverse()
ass_dict = {}
for i in range(len(assets_timestamps)):
    ass_dict[assets_timestamps[i]] = {
        assets_df_symbols[i][j]: assets_df_tokens[i][j] for j in range(len(assets_df_symbols[i]))}

    # merged[coin][timestamp] = matches[timestamp]
    # for tstamp in merged_df:
    # find closest asset that has happened
merged = dict.fromkeys(hist_timestamps)

for tstamp in merged:
    merged[tstamp] = dict.fromkeys(ass_dict[matches[tstamp]])
    for coin in ass_dict[matches[tstamp]]:
        # ass_dict[matches[tstamp]][coin]*hist_df[coin][]
        try:
            datapoints = hist_df.transpose()[coin]
            for point in datapoints:
                if point[6] == tstamp:
                    merged[tstamp][coin] = float(point[4]) * \
                        float(ass_dict[matches[tstamp]][coin])
        except (KeyError):
            merged[tstamp][coin] = 0
merged = dict(zip([datetime.utcfromtimestamp(x/1000)
              for x in merged.keys()], list(merged.values())))
fig = px.area(pd.DataFrame(merged).transpose())
fig.update_yaxes(title='$ total')
fig.update_xaxes(title='coins')
st.plotly_chart(fig)


# staked, coin holdings
for col in assets_df.columns:
    if col == 'stake_exp':
        assets_df[col] = assets_df[col].apply(
            lambda x: "" if isinstance(x, float) else x)
    else:
        assets_df[col] = assets_df[col].apply(lambda x: round(x, 2))
st.subheader('staked')
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
st.write(f"invoked: {sheets['invoke_log'].iloc[0][0][11:]}")
st.write(sheets['invoke_log'])
