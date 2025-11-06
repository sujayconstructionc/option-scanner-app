# app.py
# ⚡ Live F&O Option Scanner — Proxy-based (Cloud Safe)
# by Gunvant007 & GPT-5

import streamlit as st
import pandas as pd
import requests
import json
import time
from datetime import datetime

# ------------------ UI Setup ------------------
st.set_page_config(page_title="⚡ F&O Option Scanner", layout="wide")
st.title("⚡ Live F&O Option Scanner — Cloud Proxy Version")
st.caption("Fetches NSE Option Chain live using proxy-safe API (for Streamlit Cloud)")

# Sidebar Controls
st.sidebar.header("🧭 Filters")
ce_filter = st.sidebar.checkbox("Call (CE)", value=True)
pe_filter = st.sidebar.checkbox("Put (PE)", value=True)
combined = st.sidebar.checkbox("Combined (Both CE & PE)", value=False)
expiry_filter = st.sidebar.text_input("Expiry (e.g. 14NOV2024)", "")

delay = st.sidebar.slider("Delay between API calls (sec)", 0.5, 3.0, 1.0)
limit = st.sidebar.number_input("Top N Results", min_value=10, max_value=200, value=50, step=10)

st.sidebar.markdown("---")
st.sidebar.caption("☁️ Cloud-safe version using Proxy (auto handles cookies & rate limits)")

# ------------------ F&O Stock List ------------------
symbols = [
    "RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","LT","SBIN","AXISBANK","KOTAKBANK","HCLTECH","ITC",
    "HINDUNILVR","TITAN","MARUTI","SUNPHARMA","BAJFINANCE","NESTLEIND","ONGC","COALINDIA","TATAMOTORS",
    "WIPRO","ULTRACEMCO","TATACONSUM","GRASIM","BAJAJFINSV","NTPC","POWERGRID","ADANIPORTS","BHARTIARTL",
    "TECHM","DRREDDY","BRITANNIA","CIPLA","HEROMOTOCO","DIVISLAB","EICHERMOT","TATASTEEL","HINDALCO",
    "JSWSTEEL","UPL","INDUSINDBK","ADANIENT","BPCL","IOC","SHREECEM","HDFCLIFE","SBILIFE","ICICIPRULI",
    "M&M","BAJAJ-AUTO","PNB","DLF","CHOLAFIN","AMBUJACEM","PIDILITIND","AUROPHARMA","TATAPOWER",
    "BEL","BANDHANBNK","BIOCON","BOSCHLTD","INDIGO","CANBK","GAIL","HAVELLS","ICICIGI","LUPIN",
    "MCDOWELL-N","MFSL","MUTHOOTFIN","NMDC","PAGEIND","SAIL","SRF","TRENT","TORNTPHARM","TVSMOTOR",
    "VEDL","ZEEL","COFORGE","ABFRL","APOLLOTYRE","ASHOKLEY","BALRAMCHIN","BANKBARODA","BHEL",
    "CONCOR","CUMMINSIND","ESCORTS","GLENMARK","GNFC","GODREJCP","HINDPETRO","IDFCFIRSTB","JINDALSTEL",
    "LICHSGFIN","MRF","NAVINFLUOR","OBEROIRLTY","PIIND","RECLTD","UBL","INDHOTEL","KANSAINER","POLYCAB","OFSS"
]

# ------------------ Proxy-based NSE Fetch ------------------
def fetch_option_chain(symbol):
    proxy_url = f"https://api.allorigins.win/get?url=https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
    try:
        res = requests.get(proxy_url, timeout=10)
        if res.status_code == 200:
            data_json = json.loads(res.text)
            contents = json.loads(data_json["contents"])
            return contents
        else:
            st.warning(f"⚠️ Proxy fetch failed for {symbol}")
            return None
    except Exception as e:
        st.warning(f"⚠️ Error fetching {symbol}: {e}")
        return None

# ------------------ Process Symbol ------------------
def process_symbol(symbol):
    data = fetch_option_chain(symbol)
    if not data or "records" not in data:
        return pd.DataFrame()
    all_data = data["records"]["data"]
    rows = []
    for d in all_data:
        strike = d.get("strikePrice")
        ce = d.get("CE")
        pe = d.get("PE")

        if ce and ce_filter:
            rows.append({
                "Symbol": symbol, "Type": "CE", "Strike": strike,
                "LTP": ce.get("lastPrice"), "Volume": ce.get("totalTradedVolume"),
                "OI": ce.get("openInterest"), "Change%": ce.get("change")
            })
        if pe and pe_filter:
            rows.append({
                "Symbol": symbol, "Type": "PE", "Strike": strike,
                "LTP": pe.get("lastPrice"), "Volume": pe.get("totalTradedVolume"),
                "OI": pe.get("openInterest"), "Change%": pe.get("change")
            })
    df = pd.DataFrame(rows)
    if combined:
        return df
    return df[df["Type"].isin(["CE" if ce_filter else None, "PE" if pe_filter else None])]

# ------------------ Main ------------------
if st.button("🚀 Start Live Scan"):
    st.info("Scanning live NSE data (via proxy)... this may take 2–3 minutes for all symbols.")
    all_results = pd.DataFrame()
    for sym in symbols:
        result = process_symbol(sym)
        if not result.empty:
            all_results = pd.concat([all_results, result], ignore_index=True)
        time.sleep(delay)

    if all_results.empty:
        st.warning("⚠️ No live data received. Try again during 9:15–15:30 IST.")
    else:
        st.success("✅ Live Scan Complete")
        top = all_results.sort_values(by="Change%", ascending=False).head(limit)
        st.dataframe(top, use_container_width=True)
        csv = top.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", csv, "top_gainers.csv", "text/csv")

else:
    st.info("Press the '🚀 Start Live Scan' button to begin scanning live data.")
