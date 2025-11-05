# app.py
# Live F&O Option Scanner + Top 15 Premium Gainers
# Shows strike price, CE/PE, expiry selection
# Requirements: streamlit, pandas, numpy, requests

import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime
import math
import io

st.set_page_config(page_title="Live F&O Option Scanner", layout="wide")
st.title("⚡ Live F&O Option Scanner — Volume Spike + Top Premium Gainers")
st.caption("Live NSE option-chain scanning. Select expiry, timeframe, volume multiplier. Use reasonable delays to avoid rate limits.")

# ---------------- Sidebar controls ----------------
with st.sidebar:
    st.header("Scanner Settings")
    scan_limit = st.number_input("Scan limit (number of symbols)", min_value=10, max_value=250, value=250, step=10)
    per_call_delay = st.number_input("Delay between requests (sec)", min_value=0.2, max_value=3.0, value=1.0, step=0.1)
    timeframe = st.selectbox("Timeframe (informational)", ["1m", "5m", "15m", "1h"], index=2)
    vol_multiplier = st.number_input("Volume multiplier (spike threshold)", min_value=1.0, max_value=20.0, value=3.0, step=0.1)
    top_n_main = st.number_input("Top N results (main scanner)", min_value=5, max_value=200, value=50, step=5)
    top_n_gainers = st.number_input("Top N premium gainers (today)", min_value=5, max_value=50, value=15, step=1)
    st.markdown("---")
    st.caption("Tip: Start with scan_limit 50 and delay 1s, then increase.")

# ---------------- F&O symbol list (default ~250) ----------------
def get_default_fo_list():
    # verified list approximate; you can extend it
    return [
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

FO_SYMBOLS = get_default_fo_list()

# ---------------- Helpers ----------------
HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_option_chain(symbol):
    url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
    try:
        s = requests.Session()
        # initial get to set cookies
        s.get("https://www.nseindia.com", headers=HEADERS, timeout=5)
        r = s.get(url, headers=HEADERS, timeout=10)
        return r.json()
    except Exception as e:
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

# ---------------- UI: expiry selection (dynamic) ----------------
# fetch expiries by sampling one symbol (RELIANCE) to get expiryDates list
sample_for_expiries = st.sidebar.selectbox("Sample symbol for expiry list", ["RELIANCE"] + FO_SYMBOLS[:5])
_sample_data = fetch_option_chain(sample_for_expiries)
expiry_list = []
if _sample_data and "records" in _sample_data:
    expiry_list = _sample_data["records"].get("expiryDates", [])
expiry_choice = st.sidebar.selectbox("Select expiry (applies to scans)", ["ALL"] + expiry_list)

# ---------------- Session baseline (for top gainers) ----------------
if "baseline" not in st.session_state:
    st.session_state.baseline = {}   # keys: (symbol,strike,type) -> ltp
    st.session_state.baseline_time = None

# Baseline upload
uploaded = st.sidebar.file_uploader("Upload baseline CSV (symbol,strike,type,ltp)", type=["csv"])
if uploaded:
    try:
        df_up = pd.read_csv(uploaded)
        count = 0
        for _, r in df_up.iterrows():
            k = (str(r['symbol']).upper(), int(r['strike']), str(r['type']).upper())
            st.session_state.baseline[k] = float(r['ltp'])
            count += 1
        st.sidebar.success(f"Loaded {count} baseline rows.")
        st.session_state.baseline_time = "uploaded"
    except Exception as e:
        st.sidebar.error("Cannot parse baseline CSV")

capture_baseline_btn = st.sidebar.button("📸 Capture 9:15 Baseline (scan symbols now)")

# ---------------- Capture baseline logic ----------------
if capture_baseline_btn:
    st.sidebar.info("Capturing baseline — this may take a few minutes...")
    total = min(len(FO_SYMBOLS), int(scan_limit))
    p = st.sidebar.progress(0)
    captured = 0
    for i, sym in enumerate(FO_SYMBOLS[:total]):
        data = fetch_option_chain(sym)
        if not data or "records" not in data:
            p.progress(int((i+1)/total*100))
            time.sleep(per_call_delay)
            continue
        rec = data["records"]
        underlying = rec.get("underlyingValue", None)
        rows = rec.get("data", [])
        if not rows:
            p.progress(int((i+1)/total*100))
            time.sleep(per_call_delay)
            continue
        # detect step
        strikes = sorted({r.get('strikePrice') for r in rows})
        step = 50
        if len(strikes) > 1:
            try:
                diffs = np.diff(strikes)
                step = int(pd.Series(diffs).mode().iloc[0])
            except:
                step = 50
        atm = nearest_strike(underlying, step)
        targets = [atm, max(0, atm-step)]
        # store CE/PE lastPrice for targets (respect expiry_choice)
        for r in rows:
            sp = r.get('strikePrice')
            expd = r.get('expiryDate', None)
            if expd is None: expd = rec.get('expiryDates',[None])[0]
            if expiry_choice != "ALL" and expd != expiry_choice:
                continue
            if sp not in targets:
                continue
            for t in ['CE','PE']:
                if t in r and r[t]:
                    key = (sym.upper(), int(sp), t.upper())
                    ltp = r[t].get('lastPrice', 0) or 0.0
                    st.session_state.baseline[key] = float(ltp)
                    captured += 1
        p.progress(int((i+1)/total*100))
        time.sleep(per_call_delay)
    st.sidebar.success(f"Baseline captured: {captured} option rows.")
    st.session_state.baseline_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ---------------- Layout: two columns ----------------
col1, col2 = st.columns([2, 1])

# ---------------- Column 1: Volume Spike Scanner ----------------
with col1:
    st.header("🔹 Live Volume Spike Scanner")
    st.markdown("Scans ATM & -1 ITM strikes across symbols and shows strikes where current volume >= median_volume * volume_multiplier.")
    run_main = st.button("▶ Run Volume Spike Scan (live)")

    if run_main:
        total = min(len(FO_SYMBOLS), int(scan_limit))
        progress = st.progress(0)
        results = []
        for i, sym in enumerate(FO_SYMBOLS[:total]):
            with st.spinner(f"Scanning {sym} ({i+1}/{total})"):
                data = fetch_option_chain(sym)
                if not data or "records" not in data:
                    progress.progress(int((i+1)/total*100))
                    time.sleep(per_call_delay)
                    continue
                rec = data["records"]
                underlying = rec.get("underlyingValue", None)
                rows = rec.get("data", [])
                if not rows:
                    progress.progress(int((i+1)/total*100))
                    time.sleep(per_call_delay)
                    continue
                # optionally filter expiry
                df_rows = []
                for r in rows:
                    expd = r.get("expiryDate", None)
                    if expd is None:
                        expd = rec.get("expiryDates",[None])[0]
                    if expiry_choice != "ALL" and expd != expiry_choice:
                        continue
                    df_rows.append(r)
                if not df_rows:
                    progress.progress(int((i+1)/total*100))
                    time.sleep(per_call_delay)
                    continue

                strikes = sorted({r.get('strikePrice') for r in df_rows})
                step = 50
                if len(strikes) > 1:
                    try:
                        diffs = np.diff(strikes)
                        step = int(pd.Series(diffs).mode().iloc[0])
                    except:
                        step = 50

                atm = nearest_strike(underlying, step)
                targets = [atm, max(0, atm-step)]
                # build flattened df for median volume
                flat = []
                for r in df_rows:
                    for t in ['CE','PE']:
                        if t in r and r[t]:
                            flat.append(r[t].get('totalTradedVolume', 0) or 0)
                med_vol = np.nanmedian([v for v in flat if v>0]) or 1

                now_ts = datetime.now().strftime("%H:%M:%S")
                for r in df_rows:
                    sp = r.get('strikePrice')
                    if sp not in targets: continue
                    for t in ['CE','PE']:
                        if t in r and r[t]:
                            d = r[t]
                            vol = int(d.get('totalTradedVolume') or 0)
                            ltp = float(d.get('lastPrice') or 0.0)
                            change = float(d.get('change') or 0.0)
                            oi = int(d.get('openInterest') or 0)
                            vol_ratio = vol / med_vol if med_vol else 0
                            if vol_ratio >= vol_multiplier:
                                results.append({
                                    "Symbol": sym,
                                    "Expiry": r.get('expiryDate') or rec.get('expiryDates',[None])[0],
                                    "Strike": sp,
                                    "Type": t,
                                    "LTP": round(ltp,2),
                                    "Change": round(change,2),
                                    "Vol": vol,
                                    "OI": oi,
                                    "VolRatio": round(vol_ratio,3),
                                    "Time": now_ts
                                })
            progress.progress(int((i+1)/total*100))
            time.sleep(per_call_delay)

        if not results:
            st.warning("No volume spikes found. Try lowering volume multiplier or increasing scan time.")
        else:
            df_results = pd.DataFrame(results).sort_values(by="VolRatio", ascending=False).reset_index(drop=True)
            st.write(f"Showing Top {min(len(df_results), int(top_n_main))} results (by VolRatio)")
            st.dataframe(df_results.head(int(top_n_main)), use_container_width=True)
            st.download_button("📥 Download Volume Spike CSV", data=df_results.to_csv(index=False).encode(), file_name="volume_spike_results.csv", mime="text/csv")

# ---------------- Column 2: Top Premium Gainers ----------------
with col2:
    st.header("🚀 Today's Top Premium Gainers")
    st.markdown("Ranking by % Premium Gain vs 9:15 baseline (must capture baseline first or upload CSV).")
    if st.session_state.baseline:
        st.success(f"Baseline rows: {len(st.session_state.baseline)} (captured: {st.session_state.baseline_time})")
    else:
        st.info("No baseline loaded. Capture baseline or upload CSV in sidebar.")

    run_gainers = st.button("▶ Run Top Premium Gainers (9:15 → now)")
    if run_gainers:
        total = min(len(FO_SYMBOLS), int(scan_limit))
        prog2 = st.progress(0)
        gainers = []
        for i, sym in enumerate(FO_SYMBOLS[:total]):
            with st.spinner(f"Checking {sym} ({i+1}/{total})"):
                data = fetch_option_chain(sym)
                if not data or "records" not in data:
                    prog2.progress(int((i+1)/total*100))
                    time.sleep(per_call_delay)
                    continue
                rec = data["records"]
                underlying = rec.get("underlyingValue", None)
                rows = rec.get("data", [])
                if not rows:
                    prog2.progress(int((i+1)/total*100))
                    time.sleep(per_call_delay)
                    continue

                # optional expiry filter
                df_rows = []
                for r in rows:
                    expd = r.get("expiryDate", None)
                    if expd is None:
                        expd = rec.get('expiryDates',[None])[0]
                    if expiry_choice != "ALL" and expd != expiry_choice:
                        continue
                    df_rows.append(r)
                if not df_rows:
                    prog2.progress(int((i+1)/total*100))
                    time.sleep(per_call_delay)
                    continue

                strikes = sorted({r.get('strikePrice') for r in df_rows})
                step = 50
                if len(strikes) > 1:
                    try:
                        diffs = np.diff(strikes)
                        step = int(pd.Series(diffs).mode().iloc[0])
                    except:
                        step = 50

                atm = nearest_strike(underlying, step)
                targets = [atm, max(0, atm-step)]
                now_ts = datetime.now().strftime("%H:%M:%S")
                for r in df_rows:
                    sp = r.get('strikePrice')
                    if sp not in targets: continue
                    for t in ['CE','PE']:
                        if t in r and r[t]:
                            d = r[t]
                            curr_ltp = float(d.get('lastPrice') or 0.0)
                            vol = int(d.get('totalTradedVolume') or 0)
                            key = (sym.upper(), int(sp), t.upper())
                            base_ltp = st.session_state.baseline.get(key, None)
                            if base_ltp is None:
                                # skip if no baseline for that strike
                                continue
                            pct_gain = compute_premium_pct(curr_ltp, base_ltp)
                            gainers.append({
                                "Symbol": sym,
                                "Expiry": r.get('expiryDate') or rec.get('expiryDates',[None])[0],
                                "Strike": sp,
                                "Type": t,
                                "BaseLTP": round(base_ltp,2),
                                "CurrLTP": round(curr_ltp,2),
                                "%Gain": round(pct_gain,2),
                                "Vol": vol,
                                "Time": now_ts
                            })
            prog2.progress(int((i+1)/total*100))
            time.sleep(per_call_delay)

        if not gainers:
            st.warning("No gainers found — possibly baseline missing for many strikes. Capture baseline first.")
        else:
            df_g = pd.DataFrame(gainers).sort_values(by="%Gain", ascending=False).head(int(top_n_gainers)).reset_index(drop=True)
            st.dataframe(df_g, use_container_width=True)
            st.download_button("📥 Download Top Premium Gainers CSV", data=df_g.to_csv(index=False).encode(), file_name="top_premium_gainers.csv", mime="text/csv")

# ---------------- Footer note ----------------
st.markdown("---")
st.caption("Notes: 1) Expiry filter applies if option-chain rows include expiry dates. 2) NSE may block frequent requests — increase per_call_delay or reduce scan_limit if you see failures.")
