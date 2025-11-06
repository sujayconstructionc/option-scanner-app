# app.py — Live F&O Option Scanner (Proxy-free, Cloud-safe, NSE direct fetch)
# Streamlit cloud compatible version (Volume Spike + Top Premium Gainers)
# Author: Gunvant007 Scanner System

import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime

st.set_page_config(page_title="Live F&O Option Scanner", layout="wide")
st.title("⚡ Live F&O Option Scanner — Volume Spike + Top Premium Gainers")
st.caption("Live NSE option-chain data (direct fetch, proxy-free). Use reasonable delays to avoid rate limits.")

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("⚙️ Scanner Settings")
    scan_limit = st.number_input("Scan limit", min_value=10, max_value=250, value=250, step=10)
    per_call_delay = st.number_input("Delay between requests (sec)", min_value=0.2, max_value=3.0, value=1.0, step=0.2)
    vol_multiplier = st.number_input("Volume spike multiplier", min_value=1.0, max_value=20.0, value=3.0, step=0.5)
    top_n_main = st.number_input("Top N (Volume Spike)", min_value=5, max_value=100, value=50)
    top_n_gainers = st.number_input("Top N (Premium Gainers)", min_value=5, max_value=50, value=15)
    st.markdown("---")

# ---------------- F&O Symbol List ----------------
def get_fo_list():
    return sorted(list(set([
        "ABB","ACC","ADANIENT","ADANIPORTS","ALKEM","AMBUJACEM","APOLLOHOSP","APOLLOTYRE","ASHOKLEY",
        "ASIANPAINT","AUBANK","AUROPHARMA","AXISBANK","BAJAJ-AUTO","BAJAJFINSV","BAJFINANCE","BALKRISIND",
        "BANDHANBNK","BANKBARODA","BEL","BERGEPAINT","BHARATFORG","BHARTIARTL","BHEL","BIOCON","BOSCHLTD",
        "BPCL","BRITANNIA","CANBK","CANFINHOME","CHAMBLFERT","CHOLAFIN","CIPLA","COALINDIA","COFORGE","COLPAL",
        "CONCOR","COROMANDEL","CROMPTON","CUB","CUMMINSIND","DABUR","DALBHARAT","DEEPAKNTR","DIVISLAB","DIXON",
        "DLF","DRREDDY","EICHERMOT","ESCORTS","EXIDEIND","FEDERALBNK","GAIL","GLENMARK","GMRINFRA","GNFC",
        "GODREJCP","GRASIM","GUJGASLTD","HAL","HAVELLS","HCLTECH","HDFCBANK","HDFCLIFE","HEROMOTOCO",
        "HINDALCO","HINDCOPPER","HINDUNILVR","ICICIBANK","ICICIGI","ICICIPRULI","IDFC","IDFCFIRSTB","IGL",
        "INDIGO","INDUSINDBK","INFY","IOC","ITC","JINDALSTEL","JSWSTEEL","JUBLFOOD","KOTAKBANK","LT","LTIM",
        "LUPIN","M&M","MARUTI","MCDOWELL-N","MCX","MUTHOOTFIN","NESTLEIND","NMDC","NTPC","ONGC","PAGEIND",
        "PEL","PETRONET","PFC","PNB","POWERGRID","RECLTD","RELIANCE","SAIL","SBIN","SBILIFE","SUNPHARMA",
        "TATASTEEL","TATACONSUM","TATACHEM","TATAPOWER","TATAMOTORS","TCS","TECHM","TITAN","TRENT","UPL",
        "ULTRACEMCO","VOLTAS","WIPRO","ZEEL","ZYDUSLIFE","AARTIIND","KAYNES","POLYCAB","TORNTPOWER",
        "TVSMOTOR","VEDL","YESBANK","ZOMATO"
    ])))

FO_SYMBOLS = get_fo_list()

# ---------------- NSE Direct Fetch ----------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

def fetch_option_chain(symbol):
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=HEADERS, timeout=5)
        url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
        r = s.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            return None
    except Exception as e:
        return None

def nearest_strike(price, step=50):
    try:
        return int(round(price / step) * step)
    except:
        return None

def compute_pct(curr, base):
    try:
        return ((curr - base) / base) * 100 if base else 0
    except:
        return 0

# ---------------- Baseline Handling ----------------
if "baseline" not in st.session_state:
    st.session_state.baseline = {}
    st.session_state.baseline_time = None

if st.sidebar.button("📸 Capture 9:15 Baseline"):
    st.sidebar.info("Capturing baseline...")
    captured = 0
    for i, sym in enumerate(FO_SYMBOLS[:scan_limit]):
        data = fetch_option_chain(sym)
        if not data or "records" not in data:
            continue
        rec = data["records"]
        underlying = rec.get("underlyingValue", None)
        rows = rec.get("data", [])
        if not rows: continue
        strikes = sorted({r.get("strikePrice") for r in rows})
        step = 50 if len(strikes) < 2 else int(np.median(np.diff(sorted(strikes))))
        atm = nearest_strike(underlying, step)
        targets = [atm, atm - step]
        for r in rows:
            if r.get("strikePrice") not in targets: continue
            for t in ["CE", "PE"]:
                if t in r and r[t]:
                    st.session_state.baseline[(sym, r["strikePrice"], t)] = float(r[t].get("lastPrice", 0))
                    captured += 1
        time.sleep(per_call_delay)
    st.session_state.baseline_time = datetime.now().strftime("%H:%M:%S")
    st.sidebar.success(f"Baseline captured: {captured} rows")

# ---------------- Layout ----------------
col1, col2 = st.columns([2, 1])

# ---------------- Volume Spike Scanner ----------------
with col1:
    st.header("🔹 Volume Spike Scanner")
    if st.button("▶ Run Volume Spike Scan"):
        results = []
        total = min(len(FO_SYMBOLS), scan_limit)
        prog = st.progress(0)
        for i, sym in enumerate(FO_SYMBOLS[:total]):
            data = fetch_option_chain(sym)
            if not data or "records" not in data:
                prog.progress(int((i + 1) / total * 100))
                continue
            rec = data["records"]
            underlying = rec.get("underlyingValue", None)
            rows = rec.get("data", [])
            if not rows:
                prog.progress(int((i + 1) / total * 100))
                continue
            strikes = sorted({r.get("strikePrice") for r in rows})
            step = 50 if len(strikes) < 2 else int(np.median(np.diff(sorted(strikes))))
            atm = nearest_strike(underlying, step)
            targets = [atm, atm - step]
            vols = []
            for r in rows:
                for t in ["CE", "PE"]:
                    if t in r and r[t]:
                        vols.append(r[t].get("totalTradedVolume", 0))
            med_vol = np.median([v for v in vols if v > 0]) or 1
            for r in rows:
                if r.get("strikePrice") not in targets: continue
                for t in ["CE", "PE"]:
                    if t in r and r[t]:
                        d = r[t]
                        vol = d.get("totalTradedVolume", 0)
                        if vol / med_vol >= vol_multiplier:
                            results.append({
                                "Symbol": sym,
                                "Strike": r["strikePrice"],
                                "Type": t,
                                "LTP": d.get("lastPrice", 0),
                                "Change": d.get("change", 0),
                                "OI": d.get("openInterest", 0),
                                "Vol": vol,
                                "VolRatio": round(vol / med_vol, 2)
                            })
            prog.progress(int((i + 1) / total * 100))
            time.sleep(per_call_delay)

        if not results:
            st.warning("No volume spikes found.")
        else:
            df = pd.DataFrame(results).sort_values(by="VolRatio", ascending=False)
            st.dataframe(df.head(top_n_main), use_container_width=True)
            st.download_button("📥 Download CSV", df.to_csv(index=False), "volume_spike.csv")

# ---------------- Top Premium Gainers ----------------
with col2:
    st.header("🚀 Top Premium Gainers (vs 9:15 Baseline)")
    if st.session_state.baseline:
        st.success(f"Baseline rows: {len(st.session_state.baseline)} at {st.session_state.baseline_time}")
    else:
        st.info("Capture baseline first.")
    if st.button("▶ Run Premium Gainers"):
        gainers = []
        for i, sym in enumerate(FO_SYMBOLS[:scan_limit]):
            data = fetch_option_chain(sym)
            if not data or "records" not in data: continue
            rec = data["records"]
            underlying = rec.get("underlyingValue", None)
            rows = rec.get("data", [])
            if not rows: continue
            strikes = sorted({r.get("strikePrice") for r in rows})
            step = 50 if len(strikes) < 2 else int(np.median(np.diff(sorted(strikes))))
            atm = nearest_strike(underlying, step)
            targets = [atm, atm - step]
            for r in rows:
                if r.get("strikePrice") not in targets: continue
                for t in ["CE", "PE"]:
                    if t in r and r[t]:
                        key = (sym, r["strikePrice"], t)
                        base = st.session_state.baseline.get(key, None)
                        if base:
                            curr = float(r[t].get("lastPrice", 0))
                            pct = compute_pct(curr, base)
                            gainers.append({
                                "Symbol": sym,
                                "Strike": r["strikePrice"],
                                "Type": t,
                                "BaseLTP": base,
                                "CurrLTP": curr,
                                "%Gain": round(pct, 2)
                            })
            time.sleep(per_call_delay)
        if not gainers:
            st.warning("No gainers found.")
        else:
            df_g = pd.DataFrame(gainers).sort_values(by="%Gain", ascending=False)
            st.dataframe(df_g.head(top_n_gainers), use_container_width=True)
            st.download_button("📥 Download CSV", df_g.to_csv(index=False), "premium_gainers.csv")

st.markdown("---")
st.caption("✅ Runs live during 9:15–15:30 IST • F&O list complete • Proxy-free direct NSE fetch.")
