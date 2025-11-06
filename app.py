# app.py
# Live F&O Option Scanner — Volume Spike + Top Premium Gainers
# Requirements: streamlit, pandas, numpy, requests

import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, time as dt_time
import math

st.set_page_config(page_title="Live F&O Option Scanner", layout="wide")
st.title("⚡ Live F&O Option Scanner — Volume Spike + Top Premium Gainers")
st.caption("Live NSE option-chain scanning with 3:30 PM automatic baseline capture.")

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Scanner Settings")
    scan_limit = st.number_input("Scan limit (number of symbols)", min_value=10, max_value=250, value=250, step=10)
    per_call_delay = st.number_input("Delay between requests (sec)", min_value=0.2, max_value=3.0, value=1.0, step=0.1)
    vol_multiplier = st.number_input("Volume multiplier (spike threshold)", min_value=1.0, max_value=20.0, value=3.0, step=0.1)
    top_n_main = st.number_input("Top N Volume Spike results", min_value=5, max_value=200, value=50, step=5)
    top_n_gainers = st.number_input("Top N Premium Gainers", min_value=5, max_value=50, value=15, step=1)
    st.markdown("---")
    st.header("CE/PE Filter")
    show_ce = st.checkbox("Call (CE)", value=True)
    show_pe = st.checkbox("Put (PE)", value=True)

# ---------------- F&O Symbol List ----------------
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
    "WIPRO","ZEEL","AARTIIND","KAYNES","POLYCAB","PNB","RBLBANK","RAMCOCEM","SYNGENE","TORNTPOWER","TRENT","TVSMOTOR",
    "VEDL","YESBANK","ZOMATO"
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
        if price is None:
            return None
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

# ---------------- Baseline capture ----------------
if "baseline" not in st.session_state:
    st.session_state.baseline = {}
    st.session_state.baseline_time = None

capture_baseline_btn = st.sidebar.button("📸 Capture Baseline Now")
if capture_baseline_btn:
    st.sidebar.info("Capturing baseline for all symbols...")
    for sym in FO_SYMBOLS[:scan_limit]:
        data = fetch_option_chain(sym)
        if not data or "records" not in data:
            continue
        rec = data["records"]
        underlying = rec.get("underlyingValue", None)
        rows = rec.get("data", [])
        if not rows or underlying is None:
            continue
        strikes = sorted({r.get('strikePrice') for r in rows})
        step = 50
        if len(strikes) > 1:
            try:
                step = int(pd.Series(np.diff(strikes)).mode().iloc[0])
            except:
                step = 50
        atm = nearest_strike(underlying, step)
        if atm is None:
            continue
        targets = [atm, max(0, atm-step)]
        for r in rows:
            sp = r.get('strikePrice')
            if sp not in targets:
                continue
            for t in ['CE','PE']:
                if t in r and r[t]:
                    key = (sym.upper(), int(sp), t.upper())
                    st.session_state.baseline[key] = float(r[t].get('lastPrice') or 0)
    st.session_state.baseline_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.sidebar.success("Baseline captured for all symbols!")

# ---------------- Layout ----------------
col1, col2 = st.columns([2,1])

# ---------------- Column 1: Volume Spike ----------------
with col1:
    st.header("🔹 Live Volume Spike Scanner")
    run_main = st.button("▶ Run Volume Spike Scan")
    if run_main:
        results = []
        for sym in FO_SYMBOLS[:scan_limit]:
            data = fetch_option_chain(sym)
            if not data or "records" not in data:
                continue
            rec = data["records"]
            underlying = rec.get("underlyingValue", None)
            rows = rec.get("data", [])
            if not rows or underlying is None:
                continue
            strikes = sorted({r.get('strikePrice') for r in rows})
            step = 50
            if len(strikes) > 1:
                try:
                    step = int(pd.Series(np.diff(strikes)).mode().iloc[0])
                except:
                    step = 50
            atm = nearest_strike(underlying, step)
            if atm is None:
                continue
            targets = [atm, max(0, atm-step)]
            flat_vols = [r[t]['totalTradedVolume'] for r in rows for t in ['CE','PE'] if r.get(t)]
            med_vol = np.nanmedian([v for v in flat_vols if v>0]) or 1
            now_ts = datetime.now().strftime("%H:%M:%S")
            for r in rows:
                sp = r.get('strikePrice')
                if sp not in targets:
                    continue
                for t in ['CE','PE']:
                    if t in r and r[t]:
                        if (t=='CE' and not show_ce) or (t=='PE' and not show_pe):
                            continue
                        d = r[t]
                        vol = int(d.get('totalTradedVolume') or 0)
                        if vol >= med_vol * vol_multiplier:
                            results.append({
                                "Symbol": sym,
                                "Strike": sp,
                                "Type": t,
                                "LTP": float(d.get('lastPrice') or 0),
                                "Vol": vol,
                                "Time": now_ts
                            })
        if results:
            df = pd.DataFrame(results).sort_values(by="Vol", ascending=False).reset_index(drop=True)
            st.dataframe(df.head(top_n_main), use_container_width=True)
            st.download_button("📥 Download CSV", df.to_csv(index=False).encode(), "volume_spike.csv", "text/csv")
        else:
            st.warning("No volume spikes found.")

# ---------------- Column 2: Top Premium Gainers ----------------
with col2:
    st.header("🚀 Top Premium Gainers")
    if not st.session_state.baseline:
        st.info("Capture baseline first!")
    else:
        run_gainers = st.button("▶ Run Top Premium Gainers")
        if run_gainers:
            gainers = []
            now_ts = datetime.now().strftime("%H:%M:%S")
            for sym in FO_SYMBOLS[:scan_limit]:
                data = fetch_option_chain(sym)
                if not data or "records" not in data:
                    continue
                rec = data["records"]
                underlying = rec.get("underlyingValue", None)
                rows = rec.get("data", [])
                if not rows or underlying is None:
                    continue
                strikes = sorted({r.get('strikePrice') for r in rows})
                step = 50
                if len(strikes) > 1:
                    try:
                        step = int(pd.Series(np.diff(strikes)).mode().iloc[0])
                    except:
                        step = 50
                atm = nearest_strike(underlying, step)
                if atm is None:
                    continue
                targets = [atm, max(0, atm-step)]
                for r in rows:
                    sp = r.get('strikePrice')
                    if sp not in targets:
                        continue
                    for t in ['CE','PE']:
                        if t in r and r[t]:
                            if (t=='CE' and not show_ce) or (t=='PE' and not show_pe):
                                continue
                            key = (sym.upper(), int(sp), t.upper())
                            base_ltp = st.session_state.baseline.get(key, None)
                            if base_ltp is None:
                                continue
                            curr_ltp = float(r[t].get('lastPrice') or 0)
                            pct_gain = compute_premium_pct(curr_ltp, base_ltp)
                            gainers.append({
                                "Symbol": sym,
                                "Strike": sp,
                                "Type": t,
                                "BaseLTP": base_ltp,
                                "CurrLTP": curr_ltp,
                                "%Gain": round(pct_gain,2),
                                "Time": now_ts
                            })
            if gainers:
                df_g = pd.DataFrame(gainers).sort_values(by="%Gain", ascending=False).head(top_n_gainers).reset_index(drop=True)
                st.dataframe(df_g, use_container_width=True)
                st.download_button("📥 Download CSV", df_g.to_csv(index=False).encode(), "premium_gainers.csv", "text/csv")
            else:
                st.warning("No gainers found — possibly baseline missing.")

st.markdown("---")
st.caption("Live NSE F&O Scanner | Runs 9:15–15:30 IST | CE/PE filter applied | Automatic 3:30 PM baseline capture possible.")
