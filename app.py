import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import random

# -------------------- UI SETTINGS --------------------
st.set_page_config(page_title="F&O Option Scanner", layout="wide")
st.title("📊 F&O Option Scanner (Live Volume + Top Premium Gainers)")

tabs = st.tabs(["🔹 Volume Spike Scanner", "🚀 Top Premium Gainers"])

# -------------------- F&O STOCK LIST --------------------
fo_stocks = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "LT", "SBIN", "AXISBANK",
    "KOTAKBANK", "ITC", "HINDUNILVR", "BAJFINANCE", "BHARTIARTL", "WIPRO", "MARUTI",
    "ADANIENT", "ADANIPORTS", "HCLTECH", "POWERGRID", "SUNPHARMA", "TECHM", "ONGC",
    "TITAN", "ULTRACEMCO", "NESTLEIND", "TATASTEEL", "COALINDIA", "BRITANNIA", "BPCL",
    "EICHERMOT", "HEROMOTOCO", "HDFCLIFE", "CIPLA", "GRASIM", "NTPC", "BAJAJFINSV",
    "M&M", "UPL", "JSWSTEEL", "DIVISLAB", "DRREDDY", "INDUSINDBK", "ASIANPAINT", "TATAMOTORS",
    "SBILIFE", "HINDALCO", "APOLLOHOSP", "BAJAJ-AUTO", "ICICIPRULI", "DLF", "AMBUJACEM",
    "TATAPOWER", "BEL", "BANDHANBNK", "CHOLAFIN", "GAIL", "CANBK", "PNB", "IDFCFIRSTB",
    "ZEEL", "PEL", "VEDL", "MANAPPURAM", "FEDERALBNK", "AUROPHARMA", "INDIGO", "SRF",
    "CUMMINSIND", "SHREECEM", "CONCOR", "TORNTPHARM", "RECLTD", "NAUKRI", "MUTHOOTFIN",
    "BOSCHLTD", "PETRONET", "MFSL", "ABB", "INDHOTEL", "HAVELLS", "PIIND", "TRENT",
    "GODREJPROP", "BIOCON", "IDFC", "OFSS", "TATACOMM", "MPHASIS", "BHEL", "IRCTC",
    "HAL", "LUPIN", "OBEROIRLTY", "TVSMOTOR", "COFORGE", "POLYCAB", "DABUR", "DEEPAKNTR"
]  # ~100+ sample; can extend to 200+

# -------------------- TAB 1: Volume Spike Scanner --------------------
with tabs[0]:
    st.header("🔹 Live Volume Spike Scanner")
    timeframe = st.selectbox("Select Timeframe", ["1m", "5m", "15m", "1h"])
    vol_mult = st.slider("Volume Spike Multiplier", 1.5, 10.0, 3.0, 0.5)

    # Simulated data (in real app → replace with live NSE data)
    data = []
    for s in fo_stocks:
        prev_vol = random.randint(10000, 200000)
        curr_vol = prev_vol * random.uniform(0.5, 8)
        ltp = random.uniform(100, 3000)
        change = random.uniform(-2, 6)
        if curr_vol > prev_vol * vol_mult:
            data.append([s, round(curr_vol), round(prev_vol), round(curr_vol/prev_vol, 2), round(ltp, 2), round(change, 2), datetime.now().strftime("%H:%M:%S")])

    df1 = pd.DataFrame(data, columns=["Symbol", "CurrVol", "PrevVol", "VolRatio", "LTP", "%Change", "Time"])
    df1 = df1.sort_values("VolRatio", ascending=False)
    st.dataframe(df1, use_container_width=True)

# -------------------- TAB 2: Top Premium Gainers --------------------
with tabs[1]:
    st.header("🚀 Today's Top Premium Gainers (9:15 → Now)")
    st.info("Ranking based purely on today's % Premium Gain (ATM & -1 ITM strikes)")

    # Simulated data for top gainers
    gain_data = []
    for s in fo_stocks:
        gain = random.uniform(-5, 20)
        ltp = random.uniform(50, 300)
        gain_data.append([s, round(gain, 2), round(ltp, 2), datetime.now().strftime("%H:%M:%S")])

    df2 = pd.DataFrame(gain_data, columns=["Symbol", "% Premium Gain", "LTP", "Time"])
    df2 = df2.sort_values("% Premium Gain", ascending=False).head(15)
    st.dataframe(df2, use_container_width=True)

    st.caption("Auto-refresh every 5 min (manual reload for now).")

