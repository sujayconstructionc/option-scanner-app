# ⚡ Live F&O Option Scanner (Streamlit Cloud Safe)
# Author: Gunvant 007 | Version: Nov 2025
# Uses direct NSE API (no nsepython dependency)

import streamlit as st
import pandas as pd
import requests
import datetime as dt

st.set_page_config(page_title="⚡ Live F&O Option Scanner", layout="wide")
st.title("⚡ Live F&O Option Scanner — Cloud Compatible")
st.caption("Live NSE Option-Chain scan for all strikes (CE/PE) — auto-updates safely on Streamlit Cloud")

# ------------------ Stock List ------------------
fo_stocks = [
    "RELIANCE", "ICICIBANK", "HDFCBANK", "INFY", "SBIN", "AXISBANK", "TCS", "LT", "ITC",
    "HINDUNILVR", "KOTAKBANK", "BHARTIARTL", "SUNPHARMA", "WIPRO", "TATAMOTORS", "ADANIENT",
    "ADANIPORTS", "TATASTEEL", "TECHM", "HCLTECH", "POWERGRID", "ONGC", "COALINDIA", "M&M",
    "ULTRACEMCO", "MARUTI", "TITAN", "BAJFINANCE", "BAJAJFINSV", "HDFCLIFE", "SBILIFE", "BPCL",
    "CIPLA", "HEROMOTOCO", "EICHERMOT", "DRREDDY", "DIVISLAB", "BRITANNIA", "HINDALCO", "JSWSTEEL",
    "ADANIGREEN", "ADANIPOWER", "DMART", "DABUR", "SIEMENS", "TATACONSUM", "PIDILITIND", "TORNTPHARM",
    "AMBUJACEM", "GRASIM", "POLYCAB", "TRENT", "VOLTAS", "ZOMATO", "PNB", "CANBK", "BANKBARODA",
    "BEL", "INDIGO", "IRCTC", "BHEL", "GAIL", "IOC", "MUTHOOTFIN", "CHOLAFIN", "IDFCFIRSTB",
    "INDUSINDBK", "TVSMOTOR", "OBEROIRLTY", "NAUKRI", "KAYNES", "AARTIIND", "MFSL", "MANAPPURAM",
    "ACC", "BANDHANBNK", "SRF", "VEDL", "EXIDEIND", "JINDALSTEL", "ABFRL"
]

# ------------------ User Input ------------------
symbol = st.selectbox("📊 Select F&O Stock", fo_stocks)
expiry = st.text_input("📅 Expiry (e.g. 28-Nov-2025)", "")
scan = st.button("🔍 Scan Live Option Chain")

# ------------------ Function to Fetch NSE Data ------------------
def get_option_chain(symbol):
    url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
    headers = {
        "user-agent": "Mozilla/5.0",
        "accept-language": "en-US,en;q=0.9",
        "accept-encoding": "gzip, deflate, br"
    }
    session = requests.Session()
    session.get("https://www.nseindia.com", headers=headers)
    r = session.get(url, headers=headers)
    data = r.json()
    rows = []
    for item in data["records"]["data"]:
        strike = item["strikePrice"]
        exp = item["expiryDate"]
        ce = item.get("CE", {})
        pe = item.get("PE", {})
        if ce:
            rows.append([symbol, exp, strike, "CE", ce.get("lastPrice", 0), ce.get("change", 0),
                         ce.get("totalTradedVolume", 0), ce.get("openInterest", 0)])
        if pe:
            rows.append([symbol, exp, strike, "PE", pe.get("lastPrice", 0), pe.get("change", 0),
                         pe.get("totalTradedVolume", 0), pe.get("openInterest", 0)])
    df = pd.DataFrame(rows, columns=["Symbol", "Expiry", "Strike", "Type", "LTP", "Change", "Volume", "OI"])
    return df

# ------------------ Scanner Logic ------------------
if scan:
    with st.spinner(f"Fetching live NSE data for {symbol}..."):
        try:
            df = get_option_chain(symbol)
            if df.empty:
                st.warning("⚠️ No data received. Try again during market hours (9:15–15:30).")
            else:
                if expiry:
                    df = df[df['Expiry'].str.contains(expiry, case=False, na=False)]
                df["Premium Gain %"] = df["Change"] / (df["LTP"] - df["Change"]).replace(0, 1) * 100
                df_sorted = df.sort_values(by="Premium Gain %", ascending=False).head(15)
                st.success("✅ Live Data Fetched Successfully!")
                st.dataframe(df_sorted, use_container_width=True)

                csv = df_sorted.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download CSV", csv, f"{symbol}_option_scan.csv", "text/csv")

        except Exception as e:
            st.error(f"❌ Error fetching data: {e}")

# ------------------ Footer ------------------
st.markdown("---")
st.caption("Developed by Gunvant 007 | Live NSE API (Cloud Safe) | Version 2025.11")
