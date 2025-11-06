# app.py
# ⚡ Live F&O Option Scanner — Direct NSE API (Local Version)
# by Gunvant007 & GPT-5

import streamlit as st
import pandas as pd
import requests
import json
import time
from datetime import datetime

# ------------------ UI ------------------
st.set_page_config(page_title="⚡ F&O Option Scanner", layout="wide")
st.title("⚡ Live F&O Option Scanner — Direct NSE API (Local Version)")
st.caption("Scans all F&O stocks for Top Premium Gainers & Volume Spike (Live from NSE)")

# Sidebar Filters
st.sidebar.header("🧭 Filters")
ce_filter = st.sidebar.checkbox("Call (CE)", value=True)
pe_filter = st.sidebar.checkbox("Put (PE)", value=True)
combined = st.sidebar.checkbox("Combined (Both CE & PE)", value=False)
expiry_filter = st.sidebar.text_input("Expiry (e.g. 14NOV2024)", "")

# Delay control
delay = st.sidebar.slider("Delay between API calls (sec)", 0.5, 3.0, 1.0)

# ------------------ Symbols (F&O List) ------------------
symbols = [
    "RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","LT","SBIN","AXISBANK","KOTAKBANK","HCLTECH","ITC",
    "HINDUNILVR","TITAN","MARUTI","SUNPHARMA","BAJFINANCE","NESTLEIND","ONGC","COALINDIA","TATAMOTORS",
    "WIPRO","ULTRACEMCO","TATACONSUM","GRASIM","BAJAJFINSV","NTPC","POWERGRID","ADANIPORTS","BHARTIARTL",
    "TECHM","DRREDDY","BRITANNIA","CIPLA","HEROMOTOCO","DIVISLAB","EICHERMOT","TATASTEEL","HINDALCO",
    "JSWSTEEL","UPL","INDUSINDBK","ADANIENT","BPCL","IOC","SHREECEM","HDFCLIFE","SBILIFE","ICICIPRULI",
    "M&M","BAJAJ-AUTO","PEL","DLF","CHOLAFIN","PNB","AMBUJACEM","PIDILITIND","AUROPHARMA","TATAPOWER",
    "BEL","BANDHANBNK","BIOCON","BOSCHLTD","INDIGO","CANBK","GAIL","HAVELLS","ICICIGI","LUPIN","MCDOWELL-N",
    "MANAPPURAM","MFSL","MUTHOOTFIN","NMDC","PAGEIND","SAIL","SRF","TRENT","TORNTPHARM","TVSMOTOR","VEDL",
    "ZEEL","COFORGE","ABFRL","APOLLOTYRE","ASHOKLEY","BALRAMCHIN","BANKBARODA","BHEL","CONCOR","CUMMINSIND",
    "ESCORTS","GLENMARK","GNFC","GODREJCP","HINDPETRO","IDFCFIRSTB","JINDALSTEL","LICHSGFIN","MRF","NAVINFLUOR",
    "OBEROIRLTY","PIIND","PVRINOX","RECLTD","UBL","INDHOTEL","KANSAINER","DELTACORP","POLYCAB","OFSS","PERSISTENT"
]

# ------------------ NSE API ------------------
def fetch_option_chain(symbol):
    url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }
    try:
        sess = requests.Session()
        sess.get("https://www.nseindia.com", headers=headers, timeout=5)
        res = sess.get(url, headers=headers, timeout=5)
        data = json.loads(res.text)
        return data
    except Exception as e:
        st.warning(f"⚠️ Error fetching {symbol}: {e}")
        return None

# ------------------ Scanner Logic ------------------
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
    st.info("Scanning live data... please wait 2–3 minutes for all symbols.")
    all_results = pd.DataFrame()
    for sym in symbols:
        result = process_symbol(sym)
        if not result.empty:
            all_results = pd.concat([all_results, result], ignore_index=True)
        time.sleep(delay)

    if all_results.empty:
        st.warning("⚠️ No data fetched. Try again during market hours (9:15–15:30 IST).")
    else:
        st.success("✅ Scan complete.")
        top = all_results.sort_values(by="Change%", ascending=False).head(50)
        st.dataframe(top)
        csv = top.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", csv, "top_gainers.csv", "text/csv")

else:
    st.info("Press the '🚀 Start Live Scan' button to begin scanning live option-chain data.")
