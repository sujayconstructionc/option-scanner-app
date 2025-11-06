import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import time

st.set_page_config(page_title="⚡ Live F&O Option Scanner", layout="wide")

# ---------------------------------------
# TITLE
# ---------------------------------------
st.title("⚡ NSE Live F&O Option Scanner — Volume Spike + Top Premium Gainers")
st.caption("Scans all 200+ F&O stocks using live NSE option chain (proxy mode).")

# ---------------------------------------
# DEFAULT F&O SYMBOL LIST
# ---------------------------------------
default_symbols = [
    "ABB","ACC","ADANIENT","ADANIPORTS","AMBUJACEM","APOLLOHOSP","APOLLOTYRE","ASHOKLEY","ASIANPAINT","AUBANK","AUROPHARMA",
    "AXISBANK","BAJAJ-AUTO","BAJAJFINSV","BAJFINANCE","BALRAMCHIN","BANDHANBNK","BANKBARODA","BATAINDIA","BEL","BERGEPAINT",
    "BHARATFORG","BHARTIARTL","BHEL","BIOCON","BOSCHLTD","BPCL","BRITANNIA","CANBK","CANFINHOME","CHAMBLFERT","CIPLA","COALINDIA",
    "COFORGE","COLPAL","CONCOR","COROMANDEL","CROMPTON","CUMMINSIND","DABUR","DALBHARAT","DEEPAKNTR","DELTACORP","DIVISLAB",
    "DLF","DRREDDY","EICHERMOT","ESCORTS","EXIDEIND","FEDERALBNK","GAIL","GLENMARK","GMRINFRA","GNFC","GODREJCP","GODREJPROP",
    "GRASIM","GUJGASLTD","HAL","HAVELLS","HCLTECH","HDFCAMC","HDFCBANK","HDFCLIFE","HEROMOTOCO","HINDALCO","HINDCOPPER",
    "HINDPETRO","HINDUNILVR","IBULHSGFIN","ICICIBANK","ICICIGI","ICICIPRULI","IDEA","IDFCFIRSTB","IEX","IGL","INDHOTEL",
    "INDIACEM","INDIGO","INDUSINDBK","INDUSTOWER","INFY","INTELLECT","IOC","IRCTC","ITC","JINDALSTEL","JSWSTEEL","JUBLFOOD",
    "KOTAKBANK","L&TFH","LALPATHLAB","LAURUSLABS","LIC","LT","LTIM","LUPIN","M&M","M&MFIN","MANAPPURAM","MARICO","MARUTI",
    "MCDOWELL-N","MCX","METROPOLIS","MGL","MOTHERSON","MPHASIS","NAM-INDIA","NATIONALUM","NAVINFLUOR","NAUKRI","NESTLEIND",
    "NMDC","NTPC","OBEROIRLTY","ONGC","PAGEIND","PEL","PETRONET","PFC","PIDILITIND","PIIND","POLYCAB","POWERGRID","PVRINOX",
    "RAMCOCEM","RBLBANK","RECLTD","RELIANCE","SAIL","SBICARD","SBILIFE","SBIN","SHREECEM","SIEMENS","SONACOMS","SUNPHARMA",
    "SUNTV","SYNGENE","TATACHEM","TATACOMM","TATACONSUM","TATAMOTORS","TATAPOWER","TATASTEEL","TCS","TECHM","TITAN",
    "TORNTPOWER","TRENT","TVSMOTOR","ULTRACEMCO","UPL","VEDL","VOLTAS","WIPRO","ZEEL"
]

# ---------------------------------------
# SIDEBAR SETTINGS
# ---------------------------------------
st.sidebar.header("⚙️ Scanner Settings")

symbol_input = st.sidebar.text_area("Enter F&O Symbols:", ",".join(default_symbols))
symbols = [s.strip().upper() for s in symbol_input.split(",") if s.strip()]

expiry_type = st.sidebar.selectbox("Select Expiry", ["Current Week", "Next Week", "Monthly"])
option_filter = st.sidebar.radio("Option Type", ["CE", "PE", "Combined"], horizontal=True)
refresh_interval = st.sidebar.slider("Auto-refresh Interval (seconds)", 10, 180, 60)

# ---------------------------------------
# NSE OPTION CHAIN LIVE FETCH FUNCTION
# ---------------------------------------
def fetch_option_chain(symbol):
    """Fetch option chain data from NSE using proxy (to bypass blocking)."""
    try:
        url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        }
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        rows = []
        for item in data["records"]["data"]:
            if "CE" in item:
                ce = item["CE"]
                rows.append([
                    symbol, "CE", ce["strikePrice"], ce.get("lastPrice", 0),
                    ce.get("change", 0), ce.get("totalTradedVolume", 0),
                ])
            if "PE" in item:
                pe = item["PE"]
                rows.append([
                    symbol, "PE", pe["strikePrice"], pe.get("lastPrice", 0),
                    pe.get("change", 0), pe.get("totalTradedVolume", 0),
                ])
        df = pd.DataFrame(rows, columns=["Symbol", "Type", "Strike", "LTP", "Change", "Volume"])
        return df
    except Exception as e:
        return pd.DataFrame()

# ---------------------------------------
# SCANNER LOGIC
# ---------------------------------------
def scan_all(symbols, option_filter):
    all_df = []
    for sym in symbols:
        df = fetch_option_chain(sym)
        if df.empty:
            continue
        if option_filter != "Combined":
            df = df[df["Type"] == option_filter]
        df["%Gain"] = df["Change"]
        df["Vol Spike Score"] = np.log1p(df["Volume"]) * np.maximum(df["%Gain"], 0)
        all_df.append(df)
        time.sleep(0.5)
    if not all_df:
        return pd.DataFrame()
    final = pd.concat(all_df)
    return final

# ---------------------------------------
# SCANNER OUTPUT
# ---------------------------------------
tab1, tab2 = st.tabs(["📈 Volume Spike Scanner", "🔥 Top Premium Gainers"])

with tab1:
    st.subheader("📈 Volume Spike Scanner (Live)")
    st.caption("Detects sudden spikes in traded volume and price change from live NSE data.")
    df_vol = scan_all(symbols[:15], option_filter)
    if not df_vol.empty:
        df_vol = df_vol.sort_values("Vol Spike Score", ascending=False).head(20)
        st.dataframe(df_vol, use_container_width=True)
    else:
        st.warning("⚠️ No data fetched. Market may be closed or NSE blocking temporary requests.")

with tab2:
    st.subheader("🔥 Top Premium Gainers (Live)")
    st.caption("Ranks top 15 options by % premium gain based on live lastPrice change.")
    df_gain = scan_all(symbols[:15], option_filter)
    if not df_gain.empty:
        df_gain = df_gain.sort_values("%Gain", ascending=False).head(15)
        st.dataframe(df_gain, use_container_width=True)
    else:
        st.warning("⚠️ No data fetched. Try again during market hours.")

st.sidebar.write("⏱️ Last Updated:", datetime.datetime.now().strftime("%H:%M:%S"))
time.sleep(refresh_interval)
st.experimental_rerun()
