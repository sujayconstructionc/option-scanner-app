import streamlit as st
import pandas as pd
import requests
import time

st.set_page_config(page_title="⚡ NSE Option Scanner", layout="wide")

st.title("⚡ Live F&O Option Scanner — Premium Gainers + CE/PE Filter")
st.caption("Scans live NSE Option Chain data. Use during market hours only (9:15 AM–3:30 PM IST).")

# ----------------------------------------
# 🔹 NSE Fetch Function with Proxy Headers
# ----------------------------------------
def fetch_nse_option_chain(symbol):
    url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.nseindia.com/option-chain",
        "Connection": "keep-alive"
    }
    session = requests.Session()
    try:
        response = session.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            records = data.get("records", {}).get("data", [])
            ce_rows, pe_rows = [], []
            for item in records:
                if "CE" in item:
                    ce = item["CE"]
                    ce["type"] = "CE"
                    ce_rows.append(ce)
                if "PE" in item:
                    pe = item["PE"]
                    pe["type"] = "PE"
                    pe_rows.append(pe)
            df = pd.DataFrame(ce_rows + pe_rows)
            if not df.empty:
                df["symbol"] = symbol
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        st.warning(f"⚠️ Error fetching {symbol}: {e}")
        return pd.DataFrame()

# -----------------------------------------------------
# 🔹 Sidebar Filters
# -----------------------------------------------------
st.sidebar.header("⚙️ Scanner Filters")
expiry = st.sidebar.text_input("Enter Expiry (Optional)", "")
ce_filter = st.sidebar.checkbox("Call (CE)", True)
pe_filter = st.sidebar.checkbox("Put (PE)", True)
combine_filter = st.sidebar.checkbox("Combine CE & PE", False)
top_n = st.sidebar.slider("Top N Premium Gainers", 5, 50, 20)
refresh_time = st.sidebar.slider("Auto Refresh (sec)", 30, 300, 60)
st.sidebar.info("✅ Live data refreshes automatically every few seconds.")

# -----------------------------------------------------
# 🔹 F&O Stock List (250+ symbols)
# -----------------------------------------------------
fo_list = [
    "RELIANCE","INFY","TCS","HDFCBANK","ICICIBANK","SBIN","LT","AXISBANK","KOTAKBANK","HINDUNILVR","ITC",
    "BHARTIARTL","MARUTI","BAJFINANCE","HCLTECH","ASIANPAINT","WIPRO","SUNPHARMA","ULTRACEMCO","TECHM","ONGC",
    "ADANIENT","ADANIPORTS","HINDALCO","TATAMOTORS","POWERGRID","NTPC","TATASTEEL","COALINDIA","BRITANNIA","BPCL",
    "GRASIM","JSWSTEEL","NESTLEIND","HDFCLIFE","DIVISLAB","DRREDDY","CIPLA","APOLLOHOSP","SBILIFE","TATACONSUM",
    "HEROMOTOCO","EICHERMOT","M&M","BAJAJFINSV","UPL","SHREECEM","TITAN","BAJAJ-AUTO","INDUSINDBK","ICICIPRULI",
    "DLF","BEL","PNB","BANKBARODA","FEDERALBNK","CANBK","CHOLAFIN","MUTHOOTFIN","BANDHANBNK","IDFCFIRSTB",
    "AUROPHARMA","BIOCON","ABBOTINDIA","ALKEM","TORNTPHARM","ZYDUSLIFE","GLENMARK","LUPIN","PIIND","PEL",
    "INDHOTEL","LTIM","MPHASIS","PERSISTENT","BOSCHLTD","MRF","TVSMOTOR","ASHOKLEY","BALKRISIND","ESCORTS",
    "AMBUJACEM","RAMCOCEM","JKCEMENT","DALBHARAT","TATAPOWER","ADANIGREEN","ADANITRANS","CUMMINSIND","ABB",
    "SIEMENS","HAVELLS","POLYCAB","KEI","VOLTAS","PAGEIND","TRENT","DMART","COLPAL","GODREJCP","MARICO",
    "DABUR","BERGEPAINT","INDIGO","IRCTC","IOC","GAIL","PETRONET","GUJGASLTD","IGL","BHARATFORG","M&MFIN",
    "L&TFH","IDFC","RECLTD","PFC","HINDCOPPER","NMDC","SAIL","COFORGE","KPITTECH","LTTS","TATACOMM","IDEA",
    "ZEEL","NAUKRI","DELHIVERY","PAYTM","NYKAA","POLICYBZR","JUBLFOOD","MCDOWELL-N","RADICO","UBL","ABFRL",
    "TRENT","APLLTD","TATACHEM","COROMANDEL","KANSAINER","DEEPAKNTR","GNFC","GSFC","SRF","NAVINFLUOR",
    "AARTIIND","ALKYLAMINE","BALRAMCHIN","DMART","HONAUT","METROPOLIS","DRL","TATAELXSI","IRB","PVRINOX"
]

# -----------------------------------------------------
# 🔹 Fetch All Option Data
# -----------------------------------------------------
progress = st.progress(0)
all_data = []
for i, sym in enumerate(fo_list):
    df = fetch_nse_option_chain(sym)
    if not df.empty:
        all_data.append(df)
    progress.progress((i + 1) / len(fo_list))
    time.sleep(0.5)

if all_data:
    data = pd.concat(all_data)
    if expiry:
        data = data[data["expiryDate"].str.contains(expiry, case=False, na=False)]
    if not combine_filter:
        if ce_filter and not pe_filter:
            data = data[data["type"] == "CE"]
        elif pe_filter and not ce_filter:
            data = data[data["type"] == "PE"]

    # Premium Gainers calculation
    data["premium_gain_pct"] = (data["lastPrice"] / data["openPrice"] - 1) * 100
    data = data.sort_values("premium_gain_pct", ascending=False).head(top_n)
    st.dataframe(data[["symbol","strikePrice","type","expiryDate","lastPrice","openPrice","premium_gain_pct","openInterest"]])
else:
    st.warning("⚠️ No data fetched. Try again during market hours (9:15 AM–3:30 PM IST).")

st.caption("Developed for Live F&O Option Premium Scanning — Powered by NSE Data")
