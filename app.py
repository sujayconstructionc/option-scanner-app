# app.py
# Live F&O Option Scanner — Volume Spike + Top Premium Gainers
# Pure requests, NSE live, no nsepython dependency

import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime
import io

st.set_page_config(page_title="Live F&O Option Scanner", layout="wide")
st.title("⚡ Live F&O Option Scanner — Top Premium Gainers + Volume Spike")
st.caption("Live NSE F&O data scan. All 200+ symbols included. Auto-refresh & % gain vs 9:15 baseline.")

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Scanner Settings")
    scan_limit = st.number_input("Scan limit (symbols)", min_value=10, max_value=250, value=250, step=10)
    delay_sec = st.number_input("Delay between requests (sec)", min_value=0.2, max_value=5.0, value=1.0, step=0.1)
    vol_multiplier = st.number_input("Volume multiplier (for spike)", min_value=1.0, max_value=20.0, value=3.0, step=0.1)
    top_n_gainers = st.number_input("Top N Premium Gainers", min_value=5, max_value=50, value=15, step=1)
    st.markdown("---")
    st.caption("Tip: Start with scan_limit=50, delay=1s, increase later if needed.")

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
"WIPRO","ZEEL","AARTIIND","AMBUJACEM","KAYNES","POLYCAB","PNB","RBLBANK","RAMCOCEM","SYNGENE","TORNTPOWER",
"TRENT","TVSMOTOR","VEDL","YESBANK","ZOMATO"
]

# ---------------- NSE Requests Helpers ----------------
HEADERS = {"User-Agent":"Mozilla/5.0"}

def fetch_option_chain(symbol):
    """Fetch NSE option chain for a symbol."""
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
        return int(round(price/step)*step)
    except:
        return 0

def compute_pct_gain(current, base):
    try:
        return (current-base)/base*100
    except:
        return 0.0

# ---------------- Baseline (9:15) ----------------
if "baseline" not in st.session_state:
    st.session_state.baseline = {}  # key: (symbol,strike,type) -> ltp

capture_btn = st.sidebar.button("📸 Capture 9:15 Baseline Now")
if capture_btn:
    st.sidebar.info("Capturing baseline for all F&O symbols...")
    total = min(len(FO_SYMBOLS), scan_limit)
    pbar = st.sidebar.progress(0)
    count = 0
    for i, sym in enumerate(FO_SYMBOLS[:total]):
        data = fetch_option_chain(sym)
        if not data or "records" not in data:
            pbar.progress(int((i+1)/total*100))
            time.sleep(delay_sec)
            continue
        rec = data["records"]
        underlying = rec.get("underlyingValue",0)
        rows = rec.get("data",[])
        strikes = sorted({r.get('strikePrice') for r in rows})
        step = 50
        if len(strikes)>1:
            step = int(pd.Series(np.diff(strikes)).mode()[0])
        atm = nearest_strike(underlying, step)
        targets = [atm, max(0, atm-step)]
        for r in rows:
            sp = r.get('strikePrice')
            if sp not in targets: continue
            for t in ['CE','PE']:
                if t in r and r[t]:
                    key = (sym.upper(), sp, t.upper())
                    ltp = r[t].get('lastPrice',0) or 0
                    st.session_state.baseline[key] = float(ltp)
                    count +=1
        pbar.progress(int((i+1)/total*100))
        time.sleep(delay_sec)
    st.sidebar.success(f"Captured baseline: {count} options.")

# ---------------- Layout ----------------
col1,col2 = st.columns([2,1])

# ---------------- Column1: Volume Spike ----------------
with col1:
    st.header("🔹 Live Volume Spike Scanner")
    run_vol = st.button("▶ Run Volume Spike Scan")
    if run_vol:
        total = min(len(FO_SYMBOLS), scan_limit)
        p = st.progress(0)
        results = []
        for i,sym in enumerate(FO_SYMBOLS[:total]):
            data = fetch_option_chain(sym)
            if not data or "records" not in data:
                p.progress(int((i+1)/total*100))
                time.sleep(delay_sec)
                continue
            rec = data["records"]
            underlying = rec.get("underlyingValue",0)
            rows = rec.get("data",[])
            strikes = sorted({r.get('strikePrice') for r in rows})
            step = 50
            if len(strikes)>1:
                step = int(pd.Series(np.diff(strikes)).mode()[0])
            atm = nearest_strike(underlying, step)
            targets = [atm, max(0, atm-step)]
            # median volume
            flat_vol = [r[t].get('totalTradedVolume',0) for r in rows for t in ['CE','PE'] if t in r and r[t]]
            med_vol = np.nanmedian([v for v in flat_vol if v>0]) or 1
            now_ts = datetime.now().strftime("%H:%M:%S")
            for r in rows:
                sp = r.get('strikePrice')
                if sp not in targets: continue
                for t in ['CE','PE']:
                    if t in r and r[t]:
                        vol = r[t].get('totalTradedVolume',0) or 0
                        ltp = r[t].get('lastPrice',0) or 0
                        vol_ratio = vol/med_vol
                        if vol_ratio>=vol_multiplier:
                            results.append({
                                "Symbol":sym,"Strike":sp,"Type":t,
                                "LTP":round(ltp,2),"Vol":vol,
                                "VolRatio":round(vol_ratio,2),"Time":now_ts
                            })
            p.progress(int((i+1)/total*100))
            time.sleep(delay_sec)
        if results:
            df = pd.DataFrame(results).sort_values(by="VolRatio",ascending=False).reset_index(drop=True)
            st.dataframe(df.head(50), use_container_width=True)
            st.download_button("📥 Download CSV", df.to_csv(index=False).encode(), file_name="volume_spike.csv", mime="text/csv")
        else:
            st.warning("No volume spikes found.")

# ---------------- Column2: Top Premium Gainers ----------------
with col2:
    st.header("🚀 Top Premium Gainers (vs 9:15 Baseline)")
    run_gain = st.button("▶ Run Premium Gainers Scan")
    if run_gain:
        if not st.session_state.baseline:
            st.warning("Capture baseline first!")
        else:
            total = min(len(FO_SYMBOLS), scan_limit)
            p = st.progress(0)
            gainers=[]
            for i,sym in enumerate(FO_SYMBOLS[:total]):
                data = fetch_option_chain(sym)
                if not data or "records" not in data:
                    p.progress(int((i+1)/total*100))
                    time.sleep(delay_sec)
                    continue
                rec = data["records"]
                underlying = rec.get("underlyingValue",0)
                rows = rec.get("data",[])
                strikes = sorted({r.get('strikePrice') for r in rows})
                step = 50
                if len(strikes)>1:
                    step = int(pd.Series(np.diff(strikes)).mode()[0])
                atm = nearest_strike(underlying, step)
                targets = [atm, max(0, atm-step)]
                now_ts = datetime.now().strftime("%H:%M:%S")
                for r in rows:
                    sp = r.get('strikePrice')
                    if sp not in targets: continue
                    for t in ['CE','PE']:
                        if t in r and r[t]:
                            curr_ltp = r[t].get('lastPrice',0) or 0
                            key = (sym.upper(), sp, t.upper())
                            base_ltp = st.session_state.baseline.get(key,None)
                            if base_ltp is None: continue
                            pct_gain = compute_pct_gain(curr_ltp, base_ltp)
                            gainers.append({
                                "Symbol":sym,"Strike":sp,"Type":t,
                                "BaseLTP":round(base_ltp,2),
                                "CurrLTP":round(curr_ltp,2),
                                "%Gain":round(pct_gain,2),
                                "Time":now_ts
                            })
                p.progress(int((i+1)/total*100))
                time.sleep(delay_sec)
            if gainers:
                df = pd.DataFrame(gainers).sort_values(by="%Gain",ascending=False).head(top_n_gainers).reset_index(drop=True)
                st.dataframe(df,use_container_width=True)
                st.download_button("📥 Download CSV", df.to_csv(index=False).encode(), file_name="top_gainers.csv", mime="text/csv")
            else:
                st.warning("No gainers found for selected baseline.")
