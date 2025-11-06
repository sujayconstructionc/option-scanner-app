# ⚡ Dual F&O Option Scanner — Volume Spike + Top Premium Gainers (Live NSE API)
# Developer: Gunvant 007 | Version: 2025.11 | Cloud Safe (No nsepython)

import streamlit as st
import pandas as pd
import requests
import datetime as dt
import time

st.set_page_config(page_title="⚡ Dual F&O Option Scanner", layout="wide")
st.title("⚡ Live F&O Option Scanner — Volume Spike + Top Premium Gainers")
st.caption("Scans live NSE option-chain for all F&O stocks — CE/PE combined, top ranked by % gain and volume spike")

# -------------------- F&O Stock List --------------------
fo_stocks = [
    "RELIANCE","ICICIBANK","HDFCBANK","INFY","SBIN","AXISBANK","TCS","LT","ITC","HINDUNILVR","KOTAKBANK",
    "BHARTIARTL","SUNPHARMA","WIPRO","TATAMOTORS","ADANIENT","ADANIPORTS","TATASTEEL","TECHM","HCLTECH",
    "POWERGRID","ONGC","COALINDIA","M&M","ULTRACEMCO","MARUTI","TITAN","BAJFINANCE","BAJAJFINSV","HDFCLIFE",
    "SBILIFE","BPCL","CIPLA","HEROMOTOCO","EICHERMOT","DRREDDY","DIVISLAB","BRITANNIA","HINDALCO","JSWSTEEL",
    "ADANIGREEN","ADANIPOWER","DMART","DABUR","SIEMENS","TATACONSUM","PIDILITIND","TORNTPHARM","AMBUJACEM",
    "GRASIM","POLYCAB","TRENT","VOLTAS","ZOMATO","PNB","CANBK","BANKBARODA","BEL","INDIGO","IRCTC","BHEL",
    "GAIL","IOC","MUTHOOTFIN","CHOLAFIN","IDFCFIRSTB","INDUSINDBK","TVSMOTOR","OBEROIRLTY","NAUKRI","KAYNES",
    "AARTIIND","MFSL","MANAPPURAM","ACC","BANDHANBNK","SRF","VEDL","EXIDEIND","JINDALSTEL","ABFRL"
]

# -------------------- Sidebar Controls --------------------
st.sidebar.header("⚙️ Scanner Settings")
expiry_input = st.sidebar.text_input("Expiry (e.g. 28NOV2025)", "")
refresh_sec = st.sidebar.slider("Auto Refresh (seconds)", 10, 180, 60)
scanner_mode = st.sidebar.radio("Select Scanner Mode", ["Volume Spike", "Top Premium Gainers"])
ce_filter = st.sidebar.checkbox("Show CE", value=True)
pe_filter = st.sidebar.checkbox("Show PE", value=True)

# -------------------- Helper Functions --------------------
def fetch_option_chain(symbol):
    """Fetch NSE live option-chain JSON data"""
    try:
        url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
        headers = {
            "user-agent": "Mozilla/5.0",
            "accept-language": "en-US,en;q=0.9",
            "accept-encoding": "gzip, deflate, br"
        }
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers)
        r = session.get(url, headers=headers, timeout=10)
        data = r.json()
        rows = []
        for item in data["records"]["data"]:
            strike = item["strikePrice"]
            exp = item["expiryDate"]
            ce = item.get("CE", {})
            pe = item.get("PE", {})
            if ce and ce_filter:
                rows.append([symbol, exp, strike, "CE",
                             ce.get("lastPrice", 0),
                             ce.get("change", 0),
                             ce.get("totalTradedVolume", 0),
                             ce.get("openInterest", 0)])
            if pe and pe_filter:
                rows.append([symbol, exp, strike, "PE",
                             pe.get("lastPrice", 0),
                             pe.get("change", 0),
                             pe.get("totalTradedVolume", 0),
                             pe.get("openInterest", 0)])
        df = pd.DataFrame(rows, columns=["Symbol","Expiry","Strike","Type","LTP","Change","Volume","OI"])
        return df
    except Exception as e:
        return pd.DataFrame()

def scan_all_stocks():
    all_data = []
    for sym in fo_stocks:
        df = fetch_option_chain(sym)
        if not df.empty:
            if expiry_input:
                df = df[df["Expiry"].str.contains(expiry_input, case=False, na=False)]
            df["Premium Gain %"] = (df["Change"] / (df["LTP"] - df["Change"]).replace(0,1)) * 100
            df["Score"] = df["Premium Gain %"] * (df["Volume"]/1000)
            all_data.append(df)
        time.sleep(0.3)  # avoid NSE rate-limit
    if all_data:
        return pd.concat(all_data)
    return pd.DataFrame()

# -------------------- Main Execution --------------------
if st.button("🚀 Start Scanner"):
    placeholder = st.empty()
    while True:
        with st.spinner("Fetching live option data from NSE..."):
            df_all = scan_all_stocks()
            if df_all.empty:
                st.warning("⚠️ No live data received. Try again during 9:15–15:30 IST.")
            else:
                if scanner_mode == "Top Premium Gainers":
                    result = df_all.sort_values(by="Premium Gain %", ascending=False).head(15)
                else:
                    result = df_all.sort_values(by="Score", ascending=False).head(15)

                placeholder.dataframe(result, use_container_width=True)
                st.success(f"✅ Updated at {dt.datetime.now().strftime('%H:%M:%S')} | Mode: {scanner_mode}")

        time.sleep(refresh_sec)
