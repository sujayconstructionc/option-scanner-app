# ⚡ Live F&O Multi-Strike Option Scanner — NSE Python Version
# Author: Gunvant 007 | Updated: Nov 2025
# Description: Scans all strike prices (ATM ± multiple) for all F&O stocks using live NSE data.

import streamlit as st
import pandas as pd
from nsepython import nse_optionchain_scrape
import datetime as dt

# ------------------ Streamlit Config ------------------
st.set_page_config(page_title="⚡ Live F&O Option Scanner", layout="wide")
st.title("⚡ Live F&O Option Scanner — Multi-Strike + Volume Spike + Premium Gainers")
st.caption("Scans all strike prices (ATM ± multiple levels) for each F&O stock in real time using NSE data.")

# ------------------ F&O Stock List ------------------
fo_stocks = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "SBIN", "AXISBANK", "LT", "HINDUNILVR",
    "ITC", "BAJFINANCE", "BHARTIARTL", "KOTAKBANK", "SUNPHARMA", "HCLTECH", "MARUTI", "NESTLEIND",
    "ULTRACEMCO", "ONGC", "POWERGRID", "COALINDIA", "TATAMOTORS", "NTPC", "WIPRO", "JSWSTEEL",
    "GRASIM", "ADANIENT", "ADANIPORTS", "TITAN", "M&M", "TECHM", "TATASTEEL", "BAJAJFINSV",
    "BPCL", "CIPLA", "DIVISLAB", "EICHERMOT", "BRITANNIA", "DRREDDY", "HEROMOTOCO", "HDFCLIFE",
    "SBILIFE", "UPL", "ICICIPRULI", "INDUSINDBK", "APOLLOHOSP", "HINDALCO", "TATACONSUM",
    "TORNTPHARM", "AMBUJACEM", "PIDILITIND", "BAJAJ-AUTO", "SHREECEM", "SIEMENS", "DMART",
    "ADANIGREEN", "DABUR", "ZOMATO", "RECLTD", "IRCTC", "PNB", "CANBK", "BANKBARODA", "TVSMOTOR",
    "INDIGO", "CHOLAFIN", "BANDHANBNK", "GAIL", "MUTHOOTFIN", "IOC", "BEL", "CONCOR", "AARTIIND",
    "ABFRL", "ACC", "ALOKINDS", "BALRAMCHIN", "BHEL", "CUMMINSIND", "EXIDEIND", "FEDERALBNK",
    "GNFC", "IDFCFIRSTB", "IDEA", "INDHOTEL", "JINDALSTEL", "KAYNES", "LAURUSLABS", "MANAPPURAM",
    "MFSL", "NAUKRI", "OBEROIRLTY", "PEL", "POLYCAB", "RBLBANK", "SRF", "SUNTV", "TRENT",
    "VEDL", "VOLTAS", "ZEEL"
]

# ------------------ User Inputs ------------------
selected_stock = st.selectbox("📊 Select F&O Stock", fo_stocks)
expiry_choice = st.text_input("📅 Enter expiry date (e.g., 28-Nov-2025)", value="")
scan_button = st.button("🔍 Scan Live Option Chain")

# ------------------ Helper Function ------------------
def get_option_data(symbol):
    try:
        oc = nse_optionchain_scrape("NSE", symbol)
        ce_data = pd.DataFrame(oc['records']['data'])
        if len(ce_data) == 0:
            return None
        rows = []
        for d in oc['records']['data']:
            strike = d['strikePrice']
            ce = d.get('CE')
            pe = d.get('PE')
            if ce:
                rows.append([
                    symbol, d['expiryDate'], strike, "CE", ce.get('lastPrice', 0),
                    ce.get('change', 0), ce.get('totalTradedVolume', 0),
                    ce.get('openInterest', 0)
                ])
            if pe:
                rows.append([
                    symbol, d['expiryDate'], strike, "PE", pe.get('lastPrice', 0),
                    pe.get('change', 0), pe.get('totalTradedVolume', 0),
                    pe.get('openInterest', 0)
                ])
        df = pd.DataFrame(rows, columns=[
            "Symbol", "Expiry", "Strike", "Type", "LTP", "Change", "Volume", "OI"
        ])
        return df
    except Exception as e:
        st.warning(f"⚠️ Error fetching {symbol}: {e}")
        return None

# ------------------ Main Logic ------------------
if scan_button:
    with st.spinner(f"Fetching live option-chain data for {selected_stock}..."):
        df = get_option_data(selected_stock)
        if df is None or df.empty:
            st.error("⚠️ No data fetched. Try again during market hours (9:15 AM–3:30 PM IST).")
        else:
            if expiry_choice:
                df = df[df['Expiry'].str.contains(expiry_choice, case=False, na=False)]
            df_sorted = df.sort_values(by="Volume", ascending=False).head(10)
            st.success("✅ Live Data Fetched Successfully!")
            st.dataframe(df_sorted, use_container_width=True)

            csv = df_sorted.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", csv, f"{selected_stock}_option_scan.csv", "text/csv")

# ------------------ Footer ------------------
st.markdown("---")
st.caption("Developed by Gunvant 007 | Live NSE Data via nsepython | Version 2025.11")
