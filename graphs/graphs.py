from datetime import datetime, timedelta
import backend
import pandas as pd
import re
import plotly.express as px


def PFHistory(assets_history):
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

    # Open time, Open, High, Low, Close, Volume, Close time, Quote  asset volume, Number of trades, Taker buy base asset volume, Taker   buy quote asset volume, Ignore.
    hist_df = pd.DataFrame(
        backend.get_historical_prices(held, start)).transpose()
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
        for asset_stamp in assets_timestamps:
            if asset_stamp < hist_stamp:
                matches[hist_stamp] = asset_stamp
    assets_timestamps.reverse()
    ass_dict = {}
    for i in range(len(assets_timestamps)):
        ass_dict[assets_timestamps[i]] = {
            assets_df_symbols[i][j]: assets_df_tokens[i][j] for j in range(len(assets_df_symbols[i]))}
    merged = dict.fromkeys(hist_timestamps)
    merged_with_prices = dict.fromkeys(hist_timestamps)

    for tstamp in merged:

        merged[tstamp] = dict.fromkeys(ass_dict[matches[tstamp]])
        merged_with_prices[tstamp] = dict.fromkeys(ass_dict[matches[tstamp]])

        for coin in ass_dict[matches[tstamp]]:
            try:
                datapoints = hist_df.transpose()[coin]
                for point in datapoints:
                    if point[6] == tstamp:
                        merged_with_prices[tstamp][coin] = [float(point[4]),
                                                            float(ass_dict[matches[tstamp]][coin])]
                        merged[tstamp][coin] = float(
                            point[4]) * float(ass_dict[matches[tstamp]][coin])
            except (KeyError):
                merged[tstamp][coin] = 0
                merged_with_prices[tstamp][coin] = [0, 0]
    merged = dict(zip([datetime.utcfromtimestamp(x/1000)
                  for x in merged.keys()], list(merged.values())))
    merged_with_prices = dict(zip([datetime.utcfromtimestamp(x/1000)
                                   for x in merged_with_prices.keys()], list(merged_with_prices.values())))
    fig = px.area(pd.DataFrame(merged).transpose())
    fig.update_yaxes(title='$ total')
    fig.update_xaxes(title='coins')
    return merged_with_prices, fig


def PerfHistory(mcap_log_sheet, token_hist):
    perf_history = pd.DataFrame(
        {}, columns=[tstamp for tstamp in token_hist]).transpose()
    # actual portfolio

    # getting total pf value for each tstamp
    totals = {}
    for tstamp, _ in perf_history.iterrows():
        totals[tstamp] = sum([token_hist[tstamp][x][0] * token_hist[tstamp][x][1]
                              for x in token_hist[tstamp]])

    # normalizing
    for tstamp, _ in perf_history.iterrows():
        for coin in token_hist[tstamp]:
            price = token_hist[tstamp][coin][0]
            tokens = token_hist[tstamp][coin][1]
            token_hist[tstamp][coin] = [
                price*tokens/totals[tstamp], price]

    pf_history = {}
    first = True
    for tstamp, _ in perf_history.iterrows():
        tokens = {x: float(token_hist[tstamp][x][0])
                  for x in token_hist[tstamp]}
        prices = {x: float(token_hist[tstamp][x][1])
                  for x in token_hist[tstamp]}
        if first:
            val = 1
            pf_history[tstamp] = val
            first = False
        else:
            changes = {}
            for symbol in prices:
                try:
                    changes[symbol] = tokens[symbol]*(
                        prices[symbol] - prev_prices[symbol])/prev_prices[symbol]
                except (KeyError, ZeroDivisionError):
                    changes[symbol] = 0
            chg = 0
            for change in changes:
                chg += changes[change]
            val = chg+prev_val
            pf_history[tstamp] = val

            prev_tstamp = tstamp
        prev_val = val
        prev_prices = prices

    pf_history = {x: pf_history[x]-1 for x in pf_history}
    perf_history['pf'] = [x[1] for x in pf_history.items()]

    # mcap portfolio
    first = True
    mcap_history = {}
    first = True
    for tstamp, _ in perf_history.iterrows():
        mcap = closest_mcap(tstamp, mcap_log_sheet)
        if first:
            mcap_history[tstamp] = 1
            first = False
        else:
            new_val = mcap_history[prev_tstamp] * \
                (1+((mcap - prev_mcap)/prev_mcap))
            mcap_history[tstamp] = new_val
        prev_tstamp = tstamp
        prev_mcap = mcap
    mcap_history = {x: mcap_history[x]-1 for x in mcap_history}
    perf_history['mcap'] = mcap_history.values()

    fig = px.line(perf_history)
    return perf_history, fig


def PFPIE(assets):
    pf = {asset: round(assets[asset]['tot'] * assets[asset]
          ['new_price']) for asset in assets}
    pf_df = pd.DataFrame(pf, index=[0]).transpose()
    pf_df.columns = ['$ amt']
    pf_fig = px.pie(pf_df, values='$ amt',
                    names=[name for name in pf.keys()], hole=.3)
    pf_fig.update_traces(textposition='inside',
                         textinfo="label + percent + value")
    return pf_fig


def RBDiff(diff_matrix, token_diff):
    diff_df = pd.DataFrame(diff_matrix, index=['diff']).transpose()
    diff_df['tokens'] = token_diff
    fig = px.bar(diff_df, hover_data=[
        'tokens'])
    fig.update_layout(showlegend=False)
    fig.update_yaxes(title='$ diff')
    fig.update_xaxes(title='coins')
    return diff_df, fig


def MarketDF(gains, assets, diffs):
    perf_df = pd.DataFrame(gains, index=[
        "% gain"]).transpose()
    perf_df["% gain"] = perf_df["% gain"].apply(lambda x: float(x)*100)
    # getting market data for portfolio coins
    pf_market = backend.cmc_quotes_latest(perf_df.transpose().keys())
    market_df = {}
    for element in pf_market:
        market_df[element] = pf_market[element]['quote']['USD']
    market_df = pd.DataFrame(market_df).transpose().drop(
        columns=['last_updated', 'market_cap', 'volume_24h', 'percent_change_30d', 'percent_change_60d', 'percent_change_90d',  'percent_change_7d'])
    market_df = market_df.apply(pd.to_numeric)
    market_df.columns = ["price", "%1h", "%24h"]
    # daily % change, total dollar value, total tokens here
    assets = pd.DataFrame(assets).transpose()
    market_df.insert(loc=1, column='avg price', value=assets['avg_price'])
    market_df.insert(loc=2, column='% gain', value=perf_df['% gain'])
    market_df.insert(loc=3, column='$ diff', value=diffs['diff'])
    return market_df


def closest_mcap(tstamp, mcap_log_sheet):
    dist = timedelta(3600)
    closest_mcap = None
    for _, row in mcap_log_sheet.iterrows():
        row_time = datetime.strptime(
            row['timestamp'], '%m/%d/%Y,   %H:%M:%S')
        delta = abs(row_time - tstamp)
        if delta < dist:
            dist = delta
            closest = row_time.strftime('%m/%d/%Y, %H:%M:%S')
    for _, row in mcap_log_sheet.iterrows():
        if row['timestamp'] == closest:
            closest_mcap = row['mcap']
            break
    return closest_mcap
