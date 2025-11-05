# app.py
# Full F&O ATM/-1 ITM Option Scanner — Streamlit (auto-refresh every 15 min)
# Requirements: streamlit, pandas, numpy, requests

import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime

st.set_page_config(page_title="Live F&O Option Scanner", layout="wide", page_icon="💹")
st.title("⚡ Live F&O ATM & -1 ITM Option Scanner")
st.caption("Scans 200+ NSE F&O stocks for ATM & -1 ITM strikes, highlights volume & premium spikes. Auto-refresh every 15 min.")

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Scanner Settings")
    expiry_text = st.text_input("Expiry (optional, e.g. 28NOV2025)", value="")
    vol_multiplier = st.number_input("Volume Spike Multiplier", 1.0, 20.0, 2.0, 0.1)
    scan_limit = st.number_input("Number of F&O stocks to scan (max 250)", 5, 250, 50, 5)
    delay = st.number_input("Delay between requests (sec)", 0.2, 5.0, 1.0, 0.1)
    top_n = st.number_input("Show Top N Results", 5, 200, 50, 1)
    refresh_min = st.number_input("Auto Refresh Interval (minutes)", 1, 60, 15, 1)
    st.markdown("---")
    st.caption("💡 Recommendation: Use scan_limit 20-50 and delay 1s for first run.")

# ---------------- F&O symbols ----------------
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
    try: return int(round(price / step) * step)
    except: return None

def safe_div(a,b):
    try: return a/b if b !=0 else 0
    except: return 0

def compute_premium_pct(ltp, change):
    prev = ltp - change
    if prev and prev != 0: return (change/prev)*100
    return 0

# ---------------- Fetch NSE Option Chain ----------------
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
    if not data or "records" not in data: return []
    rec = data["records"]
    underlying = rec.get("underlyingValue", None)
    rows = rec.get("data", [])
    if not underlying or not rows: return []

    flat=[]
    for r in rows:
        sp = r.get("strikePrice")
        for t in ["CE","PE"]:
            if t in r:
                d = r[t]
                flat.append({
                    "Strike": sp,
                    "Type": t,
                    "LTP": d.get("lastPrice",0),
                    "Change": d.get("change",0),
                    "Volume": d.get("totalTradedVolume",0),
                    "OI": d.get("openInterest",0),
                    "OI Change": d.get("changeinOpenInterest",0)
                })
    df = pd.DataFrame(flat)
    if df.empty: return []

    strikes = sorted(df["Strike"].unique())
    step = 50
    if len(strikes) > 1:
        diffs = np.diff(strikes)
        try: step=int(pd.Series(diffs).mode().iloc[0])
        except: step=50

    atm = nearest_strike(underlying, step)
    target=[atm, max(0, atm-step)]
    med_vol = df["Volume"].replace(0,np.nan).median() or 1

    candidates=[]
    now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for ts in target:
        part = df[df["Strike"]==ts]
        for _,r in part.iterrows():
            ltp=float(r["LTP"]) if not pd.isna(r["LTP"]) else 0.0
            change=float(r["Change"]) if not pd.isna(r["Change"]) else 0.0
            vol=float(r["Volume"]) if not pd.isna(r["Volume"]) else 0.0
            oi=int(r["OI"]) if not pd.isna(r["OI"]) else 0
            oi_chg=float(r["OI Change"]) if not pd.isna(r["OI Change"]) else 0.0

            prem = compute_premium_pct(ltp,change)
            v_ratio = safe_div(vol,med_vol)
            oi_pct = safe_div(oi_chg,max(1,oi))*100
            score = v_ratio*(1+prem/100)

            if v_ratio>=vol_multiplier:
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

# ---------------- Auto-refresh & Run Scan ----------------
def run_scan():
    fo_symbols = get_fo_symbols()
    results=[]
    prog=st.progress(0)
    total=min(len(fo_symbols), int(scan_limit))
    for i,sym in enumerate(fo_symbols[:total]):
        with st.spinner(f"→ Scanning {sym} ({i+1}/{total})"):
            try: res=process_symbol(sym,vol_multiplier)
            except: res=[]
            if res: results.extend(res)
        prog.progress(int((i+1)/total*100))
        time.sleep(delay)
    return results

st.info(f"Auto-refreshing every {refresh_min} minutes...")

placeholder=st.empty()
while True:
    with placeholder.container():
        results=run_scan()
        if not results:
            st.warning("No spikes found — try lowering Volume multiplier or increase scan_limit.")
        else:
            df=pd.DataFrame(results).sort_values(by="Score",ascending=False).reset_index(drop=True)
            top=df.head(int(top_n))
            st.subheader(f"Top {len(top)} Option Spikes (ATM & -1 ITM)")
            st.dataframe(top,use_container_width=True)
            csv=top.to_csv(index=False).encode()
            st.download_button("📥 Download CSV",csv,"fo_option_scanner.csv",mime="text/csv")
    time.sleep(refresh_min*60)
