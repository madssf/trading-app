import streamlit as st
import backend

sheet_names = ["pf_data", "model_inputs", "staked",
               "watchlist", "deposits", "trade_log", "order_log"]
sheets = backend.get_sheets(sheet_names)

st.sidebar.title('options')
st.header('dashboard')
st.write("pf_data")
st.write(sheets["pf_data"])
st.write('model_inputs')
st.write(sheets["model_inputs"].transpose())
st.write('staked')
st.write(sheets["staked"])
st.write('trade_log')
st.write(sheets["trade_log"])
st.write('order_log')
st.write(sheets["order_log"])
st.write('deposits')
st.write(sheets["deposits"])
