# app.py
# Live F&O Option Scanner + Top Premium Gainers
# Requirements: streamlit, pandas, numpy, requests, nsepython

import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime
from nsepython import stock_info

st.set_page_config(page_title="Live F&O Option Scanner", layout="wide")
st.title("⚡ Live F&O Option Scanner — Volume Spike + Top Premium Gainers")
st.caption("Live NSE option-chain scanning for all F&O symbols. Auto-refresh for today's scan.")

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Scanner Settings")
    scan_limit = st.number_input("Scan limit (number of symbols)", min_value=10, max_value=250, value=250, step=10)
    per_call_delay = st.number_input("Delay between requests (sec)", min_value=0.2, max_value=3.0, value=1.0, step=0.1)
    vol_multiplier = st.number_input("Volume multiplier (spike threshold)", min_value=1.0, max_value=20.0, value=3.0, step=0.1)
    top_n_main = st.number_input("Top N results (main scanner)", min_value=5, max_value=200, value=50, step=5)
    top_n_gainers = st.number_input("Top N premium gainers", min_value=5, max_value=50, value=15, step=1)
    ce_filter = st.checkbox("Call (CE)", value=True)
    pe_filter = st.checkbox("Put (PE)", value=True)
    combined_filter = st.checkbox("Combined CE+PE", value=True)
    st.markdown("---")
    st.caption("Tip: Start with scan_limit 50 and delay 1s, then increase.")

# ---------------- F&O Symbol list ----------------
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

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ---------------- Helper functions ----------------
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

# ---------------- Previous day close baseline ----------------
if "baseline" not in st.session_state:
    st.session_state.baseline = {}

if st.sidebar.button("📸 Capture previous close baseline"):
    st.sidebar.info("Fetching previous day closing price for baseline...")
    captured = 0
    for sym in FO_SYMBOLS:
        try:
            prev_close = stock_info.get_quote(sym)["previousClose"]
            st.session_state.baseline[sym.upper()] = prev_close
            captured += 1
        except:
            continue
    st.sidebar.success(f"Baseline captured for {captured} symbols.")

# ---------------- Main layout ----------------
col1, col2 = st.columns([2,1])

with col1:
    st.header("🔹 Volume Spike Scanner")
    if st.button("▶ Run Volume Spike Scan (live)"):
        results = []
        for sym in FO_SYMBOLS[:scan_limit]:
            data = fetch_option_chain(sym)
            if not data or "records" not in data:
                continue
            rec = data["records"]
            underlying = rec.get("underlyingValue", None)
            rows = rec.get("data", [])
            if not rows:
                continue
            strikes = sorted({r.get('strikePrice') for r in rows})
            step = 50
            if len(strikes) > 1:
                try:
                    step = int(pd.Series(np.diff(strikes)).mode()[0])
                except:
                    step = 50
            atm = nearest_strike(underlying, step)
            if atm is None:
                continue
            targets = [atm, max(0, atm-step)]
            flat_vol = []
            for r in rows:
                for t in ["CE","PE"]:
                    if t in r and r[t]:
                        flat_vol.append(r[t].get('totalTradedVolume',0))
            med_vol = np.nanmedian([v for v in flat_vol if v>0]) or 1
            now_ts = datetime.now().strftime("%H:%M:%S")
            for r in rows:
                sp = r.get('strikePrice')
                if sp not in targets:
                    continue
                for t in ["CE","PE"]:
                    if t in r and r[t]:
                        if (t=="CE" and not ce_filter) or (t=="PE" and not pe_filter):
                            if not combined_filter:
                                continue
                        d = r[t]
                        vol = int(d.get('totalTradedVolume',0))
                        vol_ratio = vol / med_vol if med_vol else 0
                        if vol_ratio >= vol_multiplier:
                            results.append({
                                "Symbol": sym,
                                "Strike": sp,
                                "Type": t,
                                "Vol": vol,
                                "VolRatio": round(vol_ratio,3),
                                "Time": now_ts
                            })
        if results:
            df_results = pd.DataFrame(results).sort_values(by="VolRatio", ascending=False).head(top_n_main)
            st.dataframe(df_results, use_container_width=True)
            st.download_button("📥 Download Volume Spike CSV", data=df_results.to_csv(index=False).encode(), file_name="volume_spike.csv", mime="text/csv")
        else:
            st.warning("No volume spikes found.")

with col2:
    st.header("🚀 Top Premium Gainers")
    if not st.session_state.baseline:
        st.info("Capture previous close baseline first.")
    elif st.button("▶ Run Top Premium Gainers (vs prev close)"):
        gainers = []
        now_ts = datetime.now().strftime("%H:%M:%S")
        for sym in FO_SYMBOLS[:scan_limit]:
            data = fetch_option_chain(sym)
            if not data or "records" not in data:
                continue
            rec = data["records"]
            rows = rec.get("data",[])
            if not rows:
                continue
            strikes = sorted({r.get('strikePrice') for r in rows})
            step = 50
            if len(strikes) > 1:
                try:
                    step = int(pd.Series(np.diff(strikes)).mode()[0])
                except:
                    step = 50
            atm = nearest_strike(rec.get("underlyingValue",0), step)
            if atm is None:
                continue
            targets = [atm, max(0, atm-step)]
            for r in rows:
                sp = r.get("strikePrice")
                if sp not in targets:
                    continue
                for t in ["CE","PE"]:
                    if t in r and r[t]:
                        if (t=="CE" and not ce_filter) or (t=="PE" and not pe_filter):
                            if not combined_filter:
                                continue
                        d = r[t]
                        ltp = float(d.get("lastPrice",0.0))
                        prev_close = st.session_state.baseline.get(sym.upper(),0)
                        pct_gain = compute_premium_pct(ltp, prev_close)
                        gainers.append({
                            "Symbol": sym,
                            "Strike": sp,
                            "Type": t,
                            "PrevClose": prev_close,
                            "CurrLTP": ltp,
                            "%Gain": round(pct_gain,2),
                            "Time": now_ts
                        })
        if gainers:
            df_g = pd.DataFrame(gainers).sort_values(by="%Gain", ascending=False).head(top_n_gainers)
            st.dataframe(df_g, use_container_width=True)
            st.download_button("📥 Download Top Premium Gainers CSV", data=df_g.to_csv(index=False).encode(), file_name="top_gainers.csv", mime="text/csv")
        else:
            st.warning("No gainers found.")
