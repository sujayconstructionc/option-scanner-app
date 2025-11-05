# app.py
# Full F&O ATM/-1 ITM Option Scanner — Streamlit (requests-based)
# Requirements: streamlit, pandas, numpy, requests

import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime

st.set_page_config(page_title="Full F&O Option Scanner", layout="wide")
st.title("💥 Full F&O ATM & -1 ITM Option Scanner — Volume + Premium Spike")
st.caption("Scans 200+ NSE F&O stocks for ATM & -1 ITM option strikes with volume and premium analysis.")

# ---------------- Sidebar controls ----------------
with st.sidebar:
    st.header("Scanner Settings")
    expiry_text = st.text_input("Expiry (optional, e.g. 28NOV2025)", value="")
    vol_multiplier = st.number_input("Volume Spike Multiplier", 1.0, 20.0, 2.0, 0.1)
    scan_limit = st.number_input("Number of F&O stocks to scan (max 250)", 5, 250, 50, 5)
    delay = st.number_input("Delay between requests (sec)", 0.2, 5.0, 1.0, 0.1)
    top_n = st.number_input("Show Top N Results", 5, 200, 50, 1)
    st.markdown("---")
    st.caption("💡 Recommendation: Start small (scan_limit 30, delay 1s) to avoid temporary blocks.")

# ---------------- Full verified F&O symbols ----------------
def get_fo_symbols():
    fo_list = [
        "ABB","ACC","ADANIENT","ADANIPORTS","ALKEM","AMBUJACEM","APOLLOHOSP","APOLLOTYRE","ASHOKLEY",
        "ASIANPAINT","AUBANK","AUROPHARMA","AXISBANK","BAJAJ-AUTO","BAJAJFINSV","BAJFINANCE","BALKRISIND",
        "BANDHANBNK","BANKBARODA","BATAINDIA","BEL","BERGEPAINT","BHARATFORG","BHARTIARTL","BHEL","BIOCON",
        "BOSCHLTD","BPCL","BRITANNIA","CANBK","CANFINHOME","CHAMBLFERT","CHOLAFIN","CIPLA","COALINDIA",
        "COFORGE","COLPAL","CONCOR","COROMANDEL","CROMPTON","CUB","CUMMINSIND","DABUR","DALBHARAT","DEEPAKNTR",
        "DIVISLAB","DIXON","DLF","DRREDDY","EICHERMOT","ESCORTS","EXIDEIND","FEDERALBNK","GAIL","GLENMARK",
        "GMRINFRA","GNFC","GODREJCP","GRASIM","GUJGASLTD","HAL","HAVELLS","HCLTECH","HDFCAMC","HDFCBANK",
        "HDFCLIFE","HEROMOTOCO","HINDALCO","HINDCOPPER","HINDPETRO","HINDUNILVR","IBULHSGFIN","ICICIBANK",
        "ICICIGI","ICICIPRULI","IDFC","IDFCFIRSTB","IEX","IGL","INDHOTEL","INDIACEM","INDIGO","INDUSINDBK",
        "INDUSTOWER","INFY","IOC","IPCALAB","ITC","JINDALSTEL","JKCEMENT","JSWSTEEL","JUBLFOOD","KOTAKBANK",
        "L&TFH","LAURUSLABS","LICHSGFIN","LT","LTIM","LUPIN","M&M","M&MFIN","MANAPPURAM","MARICO","MARUTI",
        "MCDOWELL-N","MCX","METROPOLIS","MOTHERSON","MPHASIS","MRF","MUTHOOTFIN","NAM-INDIA","NAUKRI","NAVINFLUOR",
        "NESTLEIND","NMDC","NTPC","OBEROIRLTY","OFSS","ONGC","PAGEIND","PEL","PERSISTENT","PETRONET","PFC",
        "PIDILITIND","PIIND","PNB","POLYCAB","POWERGRID","PVRINOX","RAMCOCEM","RBLBANK","RECLTD","RELIANCE",
        "SAIL","SBICARD","SBILIFE","SBIN","SHREECEM","SIEMENS","SRF","SUNPHARMA","SUNTV","SYNGENE","TATACHEM",
        "TATACOMM","TATACONSUM","TATAMOTORS","TATAPOWER","TATASTEEL","TCS","TECHM","TITAN","TORNTPHARM","TORNTPOWER",
        "TRENT","TVSMOTOR","UBL","ULTRACEMCO","UPL","VBL","VEDL","VOLTAS","WHIRLPOOL","WIPRO","ZEEL","ZYDUSLIFE",
        "BALRAMCHIN","BANKINDIA","CENTURYTEX","GUJGASLTD","IIFL","IRCTC","JSWENERGY","NHPC","PNBHOUSING","RVNL",
        "TATAMTRDVR","TATAMTRNV","UNIONBANK","YESBANK","IRB","COCHINSHIP","POWERINDIA","INDIACEM","IDEA","CESC",
        "IDBI","NBCC","RAIN","RITES","HINDZINC","BEML","HUDCO","ITI","TIMKEN","PAYTM","KAYNES","AARTIIND",
        "POONAWALLA","KEI","DELTACORP","JYOTHYLAB","KPITTECH","POLYMED","MAZDOCK","COCHINSHIP"
    ]
    return sorted(list(set(fo_list)))

# ---------------- Utilities ----------------
def nearest_strike(price, step=50):
    try:
        return int(round(price / step) * step)
    except:
        return None

def safe_div(a, b):
    try:
        return a / b if b != 0 else 0
    except:
        return 0

def compute_premium_pct(ltp, change):
    prev = ltp - change
    if prev and prev != 0:
        return (change / prev) * 100
    return 0

# ---------------- Fetch option chain using NSE API (requests) ----------------
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

def process_symbol(sym, vol_multiplier):
    data = fetch_option_chain(sym)
    if not data or "records" not in data:
        return []

    rec = data["records"]
    underlying = rec.get("underlyingValue", None)
    rows = rec.get("data", [])
    if not underlying or not rows:
        return []

    flat = []
    for r in rows:
        sp = r.get("strikePrice")
        for t in ["CE", "PE"]:
            if t in r:
                d = r[t]
                flat.append({
                    "Strike": sp,
                    "Type": t,
                    "LTP": d.get("lastPrice", 0),
                    "Change": d.get("change", 0),
                    "Volume": d.get("totalTradedVolume", 0),
                    "OI": d.get("openInterest", 0),
                    "OI Change": d.get("changeinOpenInterest", 0)
                })
    df = pd.DataFrame(flat)
    if df.empty:
        return []

    strikes = sorted(df["Strike"].unique())
    step = 50
    if len(strikes) > 1:
        diffs = np.diff(strikes)
        try:
            mode = pd.Series(diffs).mode().iloc[0]
            if mode > 0:
                step = int(mode)
        except:
            step = 50

    atm = nearest_strike(underlying, step)
    target = [atm, max(0, atm - step)]
    med_vol = df["Volume"].replace(0, np.nan).median() or 1

    candidates = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for ts in target:
        part = df[df["Strike"] == ts]
        for _, r in part.iterrows():
            ltp = float(r["LTP"]) if not pd.isna(r["LTP"]) else 0.0
            change = float(r["Change"]) if not pd.isna(r["Change"]) else 0.0
            vol = float(r["Volume"]) if not pd.isna(r["Volume"]) else 0.0
            oi = int(r["OI"]) if not pd.isna(r["OI"]) else 0
            oi_chg = float(r["OI Change"]) if not pd.isna(r["OI Change"]) else 0.0

            prem = compute_premium_pct(ltp, change)
            v_ratio = safe_div(vol, med_vol)
            oi_pct = safe_div(oi_chg, max(1, oi)) * 100.0
            score = v_ratio * (1 + prem / 100.0)

            if v_ratio >= vol_multiplier:
                candidates.append({
                    "Symbol": sym,
                    "Expiry": expiry_text or "",
                    "Strike": ts,
                    "Type": r["Type"],
                    "LTP": round(ltp,2),
                    "Premium%": round(prem,2),
                    "Vol": int(vol),
                    "VolRatio": round(v_ratio,3),
                    "OI": oi,
                    "OIChg": oi_chg,
                    "OI%": round(oi_pct,3),
                    "Score": round(score,3),
                    "Time": now
                })
    return candidates

# ---------------- Run Scan ----------------
if st.button("🚀 Run Full F&O Scan"):
    st.info("Preparing list of F&O symbols...")
    fo_symbols = get_fo_symbols()
    st.success(f"Total F&O symbols (loaded): {len(fo_symbols)}")

    results = []
    prog = st.progress(0)
    total = min(len(fo_symbols), int(scan_limit))
    for i, sym in enumerate(fo_symbols[:total]):
        with st.spinner(f"→ Scanning {sym} ({i+1}/{total})"):
            try:
                res = process_symbol(sym, vol_multiplier)
                if res:
                    results.extend(res)
            except Exception as e:
                st.warning(f"Error for {sym}: {e}")
        prog.progress(int((i+1)/total*100))
        time.sleep(delay)

    if not results:
        st.warning("No spikes found — try lowering Volume multiplier or increase scan_limit.")
    else:
        df = pd.DataFrame(results)
        df = df.sort_values(by="Score", ascending=False).reset_index(drop=True)
        top = df.head(int(top_n))
        st.subheader(f"Top {len(top)} Option Spikes (ATM & -1 ITM)")
        st.dataframe(top, use_container_width=True)
        csv = top.to_csv(index=False).encode()
        st.download_button("📥 Download CSV", csv, "fo_option_scanner.csv", mime="text/csv")
