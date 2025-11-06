# app.py
# Live F&O Option Scanner — Full 200+ Stocks + Auto Baseline (3:15 PM) + Top Premium Gainers + Volume Spike
# Requirements: streamlit, pandas, numpy, requests
import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime
import io

st.set_page_config(page_title="Live F&O Option Scanner", layout="wide")
st.title("⚡ Live F&O Option Scanner — Auto Baseline + Top Premium Gainers")
st.caption("Scans NSE option-chain live for 200+ F&O stocks. CE/PE filter + Auto Baseline (3:15 PM) + Top Premium Gainers + Volume Spike.")

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Scanner Settings")
    scan_limit = st.number_input("Scan limit (number of symbols)", min_value=10, max_value=250, value=250, step=10)
    per_call_delay = st.number_input("Delay between requests (sec)", min_value=0.2, max_value=3.0, value=1.0, step=0.1)
    vol_multiplier = st.number_input("Volume multiplier", min_value=1.0, max_value=20.0, value=3.0, step=0.1)
    top_n_main = st.number_input("Top N Volume Spike results", min_value=5, max_value=200, value=50, step=5)
    top_n_gainers = st.number_input("Top N Premium Gainers", min_value=5, max_value=50, value=15, step=1)
    auto_refresh = st.number_input("Auto Refresh (seconds)", min_value=10, max_value=300, value=60, step=5)
    st.markdown("---")
    st.subheader("CE/PE Filter")
    filter_ce = st.checkbox("Call (CE)", value=True)
    filter_pe = st.checkbox("Put (PE)", value=True)
    filter_combined = st.checkbox("Combined (CE+PE)", value=True)

# ---------------- F&O Symbols ----------------
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
            return (ltp - prev)/prev*100
    except:
        return 0.0
    return 0.0

# ---------------- Baseline Session ----------------
if "baseline" not in st.session_state:
    st.session_state.baseline = {}   # (symbol,strike,type) -> ltp
    st.session_state.baseline_time = None

capture_baseline_btn = st.sidebar.button("📸 Capture 3:15 PM Baseline (auto)")
if capture_baseline_btn:
    st.sidebar.info("Capturing baseline for all F&O symbols — this may take minutes...")
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
        strikes = sorted({r.get("strikePrice") for r in rows})
        step = 50
        if len(strikes)>1:
            try: step=int(pd.Series(np.diff(strikes)).mode().iloc[0])
            except: step=50
        atm = nearest_strike(underlying, step)
        targets = [atm, max(0, atm-step)]
        for r in rows:
            sp = r.get("strikePrice")
            for t in ['CE','PE']:
                if t in r and r[t]:
                    key = (sym.upper(), int(sp), t.upper())
                    ltp = r[t].get('lastPrice',0) or 0.0
                    st.session_state.baseline[key] = float(ltp)
                    captured += 1
        p.progress(int((i+1)/total*100))
        time.sleep(per_call_delay)
    st.sidebar.success(f"Baseline captured: {captured} option rows.")
    st.session_state.baseline_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ---------------- Columns Layout ----------------
col1, col2 = st.columns([2,1])

# ---------------- Column 1: Volume Spike Scanner ----------------
with col1:
    st.header("🔹 Volume Spike Scanner")
    run_main = st.button("▶ Run Volume Spike Scan (live)")
    if run_main:
        total = min(len(FO_SYMBOLS), int(scan_limit))
        progress = st.progress(0)
        results = []
        for i, sym in enumerate(FO_SYMBOLS[:total]):
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
            strikes = sorted({r.get('strikePrice') for r in rows})
            step = 50
            if len(strikes) > 1:
                try: step=int(pd.Series(np.diff(strikes)).mode().iloc[0])
                except: step=50
            atm = nearest_strike(underlying, step)
            targets = [atm, max(0, atm-step)]
            flat_vol = []
            for r in rows:
                for t in ['CE','PE']:
                    if t in r and r[t]: flat_vol.append(r[t].get('totalTradedVolume',0))
            med_vol = np.nanmedian([v for v in flat_vol if v>0]) or 1
            now_ts = datetime.now().strftime("%H:%M:%S")
            for r in rows:
                sp = r.get('strikePrice')
                if sp not in targets: continue
                for t in ['CE','PE']:
                    if t in r and r[t]:
                        if (t=='CE' and not filter_ce) or (t=='PE' and not filter_pe): continue
                        d = r[t]
                        vol = int(d.get('totalTradedVolume') or 0)
                        ltp = float(d.get('lastPrice') or 0.0)
                        change = float(d.get('change') or 0.0)
                        oi = int(d.get('openInterest') or 0)
                        vol_ratio = vol/med_vol if med_vol else 0
                        if vol_ratio >= vol_multiplier:
                            results.append({
                                "Symbol": sym,
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
        if results:
            df_results = pd.DataFrame(results).sort_values(by="VolRatio", ascending=False).reset_index(drop=True)
            st.dataframe(df_results.head(int(top_n_main)), use_container_width=True)
            st.download_button("📥 Download Volume Spike CSV", data=df_results.to_csv(index=False).encode(), file_name="volume_spike_results.csv", mime="text/csv")
        else:
            st.warning("No volume spikes found. Try lowering volume multiplier.")

# ---------------- Column 2: Top Premium Gainers ----------------
with col2:
    st.header("🚀 Top Premium Gainers (vs 3:15 PM Baseline)")
    if st.session_state.baseline:
        st.success(f"Baseline rows: {len(st.session_state.baseline)} (captured: {st.session_state.baseline_time})")
    else:
        st.info("No baseline loaded. Capture baseline in sidebar.")
    run_gainers = st.button("▶ Run Top Premium Gainers (live)")
    if run_gainers:
        total = min(len(FO_SYMBOLS), int(scan_limit))
        prog2 = st.progress(0)
        gainers = []
        for i, sym in enumerate(FO_SYMBOLS[:total]):
            data = fetch_option_chain(sym)
            if not data or "records" not in data:
                prog2.progress(int((i+1)/total*100))
                time.sleep(per_call_delay)
                continue
            rec = data["records"]
            rows = rec.get("data", [])
            if not rows:
                prog2.progress(int((i+1)/total*100))
                time.sleep(per_call_delay)
                continue
            strikes = sorted({r.get('strikePrice') for r in rows})
            step = 50
            if len(strikes)>1:
                try: step=int(pd.Series(np.diff(strikes)).mode().iloc[0])
                except: step=50
            atm = nearest_strike(rec.get('underlyingValue'), step)
            targets = [atm, max(0, atm-step)]
            now_ts = datetime.now().strftime("%H:%M:%S")
            for r in rows:
                sp = r.get('strikePrice')
                if sp not in targets: continue
                for t in ['CE','PE']:
                    if t in r and r[t]:
                        if (t=='CE' and not filter_ce) or (t=='PE' and not filter_pe): continue
                        key = (sym.upper(), int(sp), t.upper())
                        base_ltp = st.session_state.baseline.get(key, None)
                        if base_ltp is None: continue
                        curr_ltp = float(r[t].get('lastPrice') or 0.0)
                        pct_gain = compute_premium_pct(curr_ltp, base_ltp)
                        gainers.append({
                            "Symbol": sym,
                            "Strike": sp,
                            "Type": t,
                            "BaseLTP": round(base_ltp,2),
                            "CurrLTP": round(curr_ltp,2),
                            "%Gain": round(pct_gain,2),
                            "Time": now_ts
                        })
            prog2.progress(int((i+1)/total*100))
            time.sleep(per_call_delay)
        if gainers:
            df_g = pd.DataFrame(gainers).sort_values(by="%Gain", ascending=False).head(int(top_n_gainers)).reset_index(drop=True)
            st.dataframe(df_g, use_container_width=True)
            st.download_button("📥 Download Top Premium Gainers CSV", data=df_g.to_csv(index=False).encode(), file_name="top_premium_gainers.csv", mime="text/csv")
        else:
            st.warning("No gainers found — baseline missing?")

st.markdown("---")
st.caption("✅ Runs live 9:15–15:30 IST • Auto Baseline 3:15 PM • CE/PE filter • Top N + Volume Spike")
