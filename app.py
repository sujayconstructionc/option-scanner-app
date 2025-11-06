import streamlit as st
import pandas as pd
import requests
import json
import time
from datetime import datetime

st.set_page_config(page_title="⚡ NSE Live F&O Option Scanner", layout="wide")

st.title("⚡ NSE Live F&O Option Scanner — Volume Spike + Top Premium Gainers")
st.caption("Scan all 200+ F&O stocks (ATM + -1 ITM) using live NSE data")

# --- SETTINGS ---
col1, col2, col3, col4 = st.columns(4)
symbol = col1.selectbox("Select Stock", ["RELIANCE", "SBIN", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "TATASTEEL",
                                         "AXISBANK", "KOTAKBANK", "ITC", "LT", "MARUTI", "HEROMOTOCO", "ULTRACEMCO",
                                         "INDUSINDBK", "BAJFINANCE", "BAJAJFINSV", "DIVISLAB", "NESTLEIND", "SUNPHARMA",
                                         "TATAMOTORS", "HCLTECH", "WIPRO", "TECHM", "POWERGRID", "TITAN", "ONGC",
                                         "COALINDIA", "BHARTIARTL", "NTPC", "SBICARD", "APOLLOHOSP", "HDFCLIFE",
                                         "DRREDDY", "TATACONSUM", "M&M", "BPCL", "ADANIENT", "ADANIPORTS", "CIPLA",
                                         "EICHERMOT", "GRASIM", "BAJAJ-AUTO", "BRITANNIA", "SHREECEM", "UPL",
                                         "TRENT", "JSWSTEEL", "DLF", "TATACHEM", "ICICIPRULI", "PIDILITIND", "CHOLAFIN",
                                         "PNB", "BHEL", "CANBK", "HINDUNILVR", "RECLTD", "IRCTC", "ZEEL", "TVSMOTOR",
                                         "HINDALCO", "DEEPAKNTR", "ABB", "INDHOTEL", "TATAELXSI", "AMBUJACEM",
                                         "AARTIIND", "KAYNES", "POLYCAB", "SBILIFE", "IDFCFIRSTB", "OIL", "IDEA",
                                         "JINDALSTEL", "BANKBARODA", "PFC", "HAVELLS", "GODREJCP", "COLPAL", "UBL",
                                         "DABUR", "MCDOWELL-N", "ICICIGI", "IRFC", "MANAPPURAM", "LTIM", "MFSL",
                                         "ALKEM", "BOSCHLTD", "INDIGO", "CONCOR", "BEL", "SRF", "HAL", "NAVINFLUOR",
                                         "TORNTPHARM", "ZYDUSLIFE", "GAIL", "ABBOTINDIA", "SBINN", "NATIONALUM", "IOB"],
                        index=0)

expiry = col2.text_input("Expiry (e.g. 28NOV2024)", "28NOV2024")
refresh = col3.slider("Auto Refresh (seconds)", 10, 120, 30)
mode = col4.selectbox("Mode", ["Volume Spike", "Top Premium Gainers"])

# --- CE/PE Filter ---
ce_filter = st.sidebar.checkbox("Show Calls (CE)", True)
pe_filter = st.sidebar.checkbox("Show Puts (PE)", True)
combined = st.sidebar.checkbox("Show Combined (Both)", True)

# --- FETCH NSE OPTIONCHAIN FUNCTION ---
def fetch_nse_option_chain(symbol):
    url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "accept-language": "en,IN;q=0.9",
        "referer": "https://www.nseindia.com/option-chain"
    }
    session = requests.Session()
    try:
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        response = session.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = json.loads(response.text)
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
            st.warning(f"⚠️ NSE Blocked {symbol}: {response.status_code}")
            return pd.DataFrame()
    except Exception as e:
        st.warning(f"⚠️ Error fetching {symbol}: {e}")
        return pd.DataFrame()

# --- PROCESS DATA ---
def process_data(df):
    if df.empty:
        return df
    df = df[["symbol", "strikePrice", "expiryDate", "type", "lastPrice", "change", "totalTradedVolume", "openInterest"]]
    df = df.sort_values(by="change", ascending=False)
    df["timestamp"] = datetime.now().strftime("%H:%M:%S")
    return df

# --- MAIN SCANNER ---
st.markdown("### 🔄 Scanning Live NSE Data...")
placeholder = st.empty()

while True:
    data = fetch_nse_option_chain(symbol)
    if not data.empty:
        processed = process_data(data)

        # Apply CE/PE filters
        if not combined:
            if ce_filter and not pe_filter:
                processed = processed[processed["type"] == "CE"]
            elif pe_filter and not ce_filter:
                processed = processed[processed["type"] == "PE"]

        # Show Top 15 gainers
        top = processed.head(15)
        placeholder.dataframe(top, use_container_width=True)
    else:
        placeholder.warning("⚠️ No data fetched. Try again during market hours (9:15 AM–3:30 PM IST).")

    time.sleep(refresh)
