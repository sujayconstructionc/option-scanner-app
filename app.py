# app.py
# Live F&O Option Scanner + Top Premium Gainers
# Requirements: streamlit, pandas, numpy, requests

import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime
import io

st.set_page_config(page_title="Live F&O Option Scanner", layout="wide")
st.title("⚡ Live F&O Option Scanner — Volume Spike + Top Premium Gainers")
st.caption("Live NSE option-chain scanning. Use reasonable delays to avoid rate limits.")

# ---------------- Sidebar controls ----------------
with st.sidebar:
    st.header("Scanner Settings")
    scan_limit = st.number_input("Scan limit (number of symbols)", min_value=10, max_value=250, value=250, step=10)
    per_call_delay = st.number_input("Delay between requests (sec)", min_value=0.2, max_value=3.0, value=1.0, step=0.1)
    vol_multiplier = st.number_input("Volume multiplier (spike threshold)", min_value=1.0, max_value=20.0, value=3.0, step=0.1)
    top_n_main = st.number_input("Top N results (Volume Spike)", min_value=5, max_value=200, value=50, step=5)
    top_n_gainers = st.number_input("Top N Premium Gainers", min_value=5, max_value=50, value=15, step=1)
    st.markdown("---")
    st.caption("Tip: Start with scan_limit 50 and delay 1s, then increase.")

# ---------------- F&O symbol list ----------------
FO_SYMBOLS = [
    "ABB","ACC","ADANIENT","ADANIPORTS","ALKEM","AMBUJACEM","APOLLOHOSP","APOLLOTYRE","ASHOKLEY",
    "ASIANPAINT","AUBANK","AUROPHARMA","AXISBANK","BAJAJ-AUTO","BAJAJFINSV","BAJFINANCE","BALKRISIND",
    "BANDHANBNK","BANKBARODA","BATAINDIA","BEL","BERGEPAINT","BHARATFORG","BHARTIARTL","BHEL","BIOCON",
    "BOSCHLTD","BPCL","BRITANNIA","CANBK","CANFINHOME","CHAMBLFERT","CHOLAFIN","CIPLA","COALINDIA",
    "COFORGE","COLPAL","CONCOR","COROMANDEL","CROMPTON","CUB","CUMMINSIND","DABUR","DALBHARAT","DEEPAKNTR",
    "DIVISLAB","DIXON","DLF","DRREDDY","EICHERMOT","ESCORTS","EXIDEIND","FEDERALBNK","GAIL","GLENMARK",
    "GMRINFRA","GNFC","GODREJCP","GRASIM","GUJGASLTD","HAL","HAVELLS","HCLTECH","HDFCBANK","HDFCLIFE",
    "HEROMOTOCO","HINDALCO","HINDCOPPER","HINDUNILVR","ICICIBANK","ICICIGI","ICICIPRULI","IDFC","IDFCFIRSTB",
    "IGL","INDIGO","INDUSINDBK","INFY","IOC","ITC","JINDALSTEL","JSWSTEEL","JUBLFOOD","KOTAKBANK","LT","LTIM",
    "LUPIN","M&M","MARUTI","MCDOWELL-N","MCX","MUTHOOTFIN","NESTLEIND","NMDC","NTPC","ONGC","PAGEIND","PEL",
    "PETRONET","POWERGRID","RELIANCE","SAIL","SBIN","SBILIFE","SUNPHARMA","TATASTEEL","TCS","TITAN","UPL","VOLTAS",
    "WIPRO","ZEEL","AARTIIND","AMBUJACEM","KAYNES","POLYCAB","PNB","RBLBANK","RAMCOCEM","SYNGENE","TORNTPOWER",
    "TRENT","TVSMOTOR","VEDL","YESBANK","ZOMATO"
]

# ---------------- Helpers ----------------
HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_option_chain(symbol):
    url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=HEADERS, timeout=5)
        r = s.get(url, headers=HEADERS, timeout=10)
        return r.json()
    except:
        return None

def nearest_strike(price, step=50):
    try:
        return int(round(price/step) * step)
    except:
        return None

def compute_premium_pct(ltp, prev):
    try:
        if prev and prev != 0:
            return (ltp - prev) / prev * 100.0
    except:
        pass
    return 0.0

# ---------------- UI: expiry selection ----------------
sample_symbol = st.sidebar.selectbox("Sample symbol for expiry list", ["RELIANCE"] + FO_SYMBOLS[:5])
_sample_data = fetch_option_chain(sample_symbol)
expiry_list = []
if _sample_data and "records" in _sample_data:
    expiry_list = _sample_data["records"].get("expiryDates", [])
expiry_choice = st.sidebar.selectbox("Select expiry (applies to scans)", ["ALL"] + expiry_list)

# ---------------- Session baseline ----------------
if "baseline" not in st.session_state:
    st.session_state.baseline = {}
    st.session_state.baseline_time = None

# Baseline capture button
if st.sidebar.button("📸 Capture 9:15 Baseline"):
    st.sidebar.info("Capturing 9:15 baseline...")
    for sym in FO_SYMBOLS:
        data = fetch_option_chain(sym)
        if not data or "records" not in data:
            continue
        rec = data["records"]
        underlying = rec.get("underlyingValue", None)
        rows = rec.get("data", [])
        strikes = sorted({r.get('strikePrice') for r in rows})
        step = 50
        if len(strikes) > 1:
            try:
                step = int(pd.Series(np.diff(strikes)).mode().iloc[0])
            except:
                step = 50
        atm = nearest_strike(underlying, step)
        targets = [atm, max(0, atm-step)]
        for r in rows:
            sp = r.get('strikePrice')
            if sp not in targets:
                continue
            for t in ['CE','PE']:
                if t in r and r[t]:
                    key = (sym.upper(), int(sp), t.upper())
                    st.session_state.baseline[key] = float(r[t].get('lastPrice') or 0)
    st.sidebar.success("Baseline captured.")

# ---------------- Layout ----------------
col1, col2 = st.columns([2,1])

# ---------------- Column 1: Volume Spike ----------------
with col1:
    st.header("🔹 Volume Spike Scanner")
    if st.button("▶ Run Volume Spike Scan"):
        results = []
        for sym in FO_SYMBOLS[:scan_limit]:
            data = fetch_option_chain(sym)
            if not data or "records" not in data:
                continue
            rec = data["records"]
            underlying = rec.get("underlyingValue", None)
            rows = rec.get("data", [])
            strikes = sorted({r.get('strikePrice') for r in rows})
            step = 50
            if len(strikes) > 1:
                try:
                    step = int(pd.Series(np.diff(strikes)).mode().iloc[0])
                except:
                    step = 50
            atm = nearest_strike(underlying, step)
            targets = [atm, max(0, atm-step)]
            flat_vol = [r[t]['totalTradedVolume'] for r in rows for t in ['CE','PE'] if t in r and r[t]]
            median_vol = np.median(flat_vol) if flat_vol else 1
            now_ts = datetime.now().strftime("%H:%M:%S")
            for r in rows:
                sp = r.get('strikePrice')
                if sp not in targets:
                    continue
                for t in ['CE','PE']:
                    if t in r and r[t]:
                        vol = r[t].get('totalTradedVolume',0)
                        vol_ratio = vol / median_vol if median_vol else 0
                        if vol_ratio >= vol_multiplier:
                            results.append({
                                "Symbol": sym,
                                "Expiry": r.get('expiryDate',None),
                                "Strike": sp,
                                "Type": t,
                                "LTP": r[t].get('lastPrice',0),
                                "Vol": vol,
                                "VolRatio": round(vol_ratio,2),
                                "Time": now_ts
                            })
        if results:
            df_res = pd.DataFrame(results).sort_values(by="VolRatio", ascending=False).head(top_n_main)
            st.dataframe(df_res,use_container_width=True)
            st.download_button("📥 Download CSV", data=df_res.to_csv(index=False).encode(), file_name="volume_spike.csv")
        else:
            st.warning("No volume spikes found.")

# ---------------- Column 2: Top Premium Gainers ----------------
with col2:
    st.header("🚀 Top Premium Gainers")
    if st.session_state.baseline:
        st.success(f"Baseline captured: {len(st.session_state.baseline)} rows")
    else:
        st.info("No baseline loaded. Capture first.")
    if st.button("▶ Run Premium Gainers Scan"):
        gainers = []
        for sym in FO_SYMBOLS[:scan_limit]:
            data = fetch_option_chain(sym)
            if not data or "records" not in data:
                continue
            rec = data["records"]
            rows = rec.get("data", [])
            strikes = sorted({r.get('strikePrice') for r in rows})
            step = 50
            if len(strikes) > 1:
                try:
                    step = int(pd.Series(np.diff(strikes)).mode().iloc[0])
                except:
                    step = 50
            atm = nearest_strike(rec.get('underlyingValue',0), step)
            targets = [atm, max(0, atm-step)]
            now_ts = datetime.now().strftime("%H:%M:%S")
            for r in rows:
                sp = r.get('strikePrice')
                if sp not in targets:
                    continue
                for t in ['CE','PE']:
                    if t in r and r[t]:
                        key = (sym.upper(), int(sp), t.upper())
                        base = st.session_state.baseline.get(key)
                        if base:
                            curr = r[t].get('lastPrice',0)
                            pct_gain = compute_premium_pct(curr, base)
                            gainers.append({
                                "Symbol": sym,
                                "Expiry": r.get('expiryDate',None),
                                "Strike": sp,
                                "Type": t,
                                "BaseLTP": base,
                                "CurrLTP": curr,
                                "%Gain": round(pct_gain,2),
                                "Time": now_ts
                            })
        if gainers:
            df_gain = pd.DataFrame(gainers).sort_values(by="%Gain", ascending=False).head(top_n_gainers)
            st.dataframe(df_gain,use_container_width=True)
            st.download_button("📥 Download CSV", data=df_gain.to_csv(index=False).encode(), file_name="premium_gainers.csv")
        else:
            st.warning("No gainers found.")
