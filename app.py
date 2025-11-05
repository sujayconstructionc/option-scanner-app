# app.py
# Live F&O Option Scanner + Top 15 Premium Gainers
# Requirements: streamlit, pandas, numpy, requests

import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime

st.set_page_config(page_title="Live F&O Option Scanner", layout="wide")
st.title("⚡ Live F&O Option Scanner — Volume Spike + Top Premium Gainers")
st.caption("Scan NSE option-chain live. Use reasonable delays to avoid rate limits.")

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
    st.header("Filters")
    filter_call = st.checkbox("Call (CE)", value=True)
    filter_put = st.checkbox("Put (PE)", value=True)
    filter_combined = st.checkbox("Combined CE+PE", value=True)
    st.markdown("---")
    st.caption("Tip: Start with scan_limit 50 and delay 1s, then increase.")

# ---------------- F&O symbol list (200+ symbols) ----------------
FO_SYMBOLS = [
    "ABB","ACC","ADANIENT","ADANIPORTS","ALKEM","AMBUJACEM","APOLLOHOSP","APOLLOTYRE","ASHOKLEY",
    "ASIANPAINT","AUBANK","AUROPHARMA","AXISBANK","BAJAJ-AUTO","BAJAJFINSV","BAJFINANCE","BALKRISIND",
    "BANDHANBNK","BANKBARODA","BATAINDIA","BEL","BERGEPAINT","BHARATFORG","BHARTIARTL","BHEL","BIOCON",
    "BOSCHLTD","BPCL","BRITANNIA","CANBK","CANFINHOME","CHAMBLFERT","CHOLAFIN","CIPLA","COALINDIA",
    "COFORGE","COLPAL","CONCOR","COROMANDEL","CROMPTON","CUB","CUMMINSIND","DABUR","DALBHARAT","DEEPAKNTR",
    "DIVISLAB","DIXON","DLF","DRREDDY","EICHERMOT","ESCORTS","EXIDEIND","FEDERALBNK","GAIL","GLENMARK",
    "GMRINFRA","GNFC","GODREJCP","GRASIM","GUJGASLTD","HAL","HAVELLS","HCLTECH","HDFCBANK","HDFCLIFE",
    "HEROMOTOCO","HINDALCO","HINDCOPPER","HINDUNILVR","ICICIBANK","ICICIGI","ICICIPRULI","IDFCFIRSTB",
    "IGL","INDIGO","INDUSINDBK","INFY","IOC","ITC","JINDALSTEL","JSWSTEEL","JUBLFOOD","KOTAKBANK",
    "L&TFH","LT","LTIM","LUPIN","M&M","MARUTI","MCDOWELL-N","MCX","MUTHOOTFIN","NESTLEIND","NMDC",
    "NTPC","ONGC","PAGEIND","PEL","PETRONET","POWERGRID","RELIANCE","SAIL","SBIN","SBILIFE","SUNPHARMA",
    "TATASTEEL","TCS","TITAN","UPL","VOLTAS","WIPRO","ZEEL","AARTIIND","AMBUJACEM","KAYNES","POLYCAB",
    "PNB","RBLBANK","RAMCOCEM","SYNGENE","TORNTPOWER","TRENT","TVSMOTOR","VEDL","YESBANK","ZOMATO",
    "ADANIGREEN","ADANITRANS","APLLTD","BAJAJHLDNG","BERGEPAINT","CAMS","DELTACORP","DIVISLAB","EIHOTEL",
    "GRSE","ICICIPRULI","INDHOTEL","INFRATEL","JUBILANT","LALPATHLAB","LTI","MANAPPURAM","MOIL","NHPC",
    "OBEROIRLTY","PETRONET","POLYCAB","PNBHOUSING","PRSMJOHNSN","RAJESHEXPO","RBLBANK","RECLTD","SJVN",
    "SRF","STARHEALTH","SUNTV","TATACHEM","TATACOMM","TATACONSUM","TATAPOWER","TV18BRDCST","UPL","VBL",
    "VIPIND","VOLTRONIC","ZYDUSLIFE"
]

# ---------------- NSE option-chain fetch ----------------
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

# ---------------- Helpers ----------------
def nearest_strike(price, step=50):
    try:
        return int(round(price/step)*step)
    except:
        return None

def compute_premium_pct(ltp, prev):
    try:
        if prev and prev != 0:
            return (ltp - prev) / prev * 100.0
    except:
        pass
    return 0.0

# ---------------- Expiry list ----------------
sample_for_expiries = st.sidebar.selectbox("Sample symbol for expiry list", ["RELIANCE"] + FO_SYMBOLS[:5])
_sample_data = fetch_option_chain(sample_for_expiries)
expiry_list = []
if _sample_data and "records" in _sample_data:
    expiry_list = _sample_data["records"].get("expiryDates", [])
expiry_choice = st.sidebar.selectbox("Select expiry", ["ALL"] + expiry_list)

# ---------------- Baseline capture ----------------
if "baseline" not in st.session_state:
    st.session_state.baseline = {}   # keys: (symbol,strike,type)
    st.session_state.baseline_time = None

uploaded = st.sidebar.file_uploader("Upload baseline CSV", type=["csv"])
if uploaded:
    try:
        df_up = pd.read_csv(uploaded)
        for _, r in df_up.iterrows():
            key = (str(r['symbol']).upper(), int(r['strike']), str(r['type']).upper())
            st.session_state.baseline[key] = float(r['ltp'])
        st.session_state.baseline_time = "uploaded"
        st.sidebar.success(f"Baseline loaded: {len(df_up)} rows")
    except:
        st.sidebar.error("Cannot parse baseline CSV")

capture_baseline_btn = st.sidebar.button("📸 Capture 9:15 Baseline")
if capture_baseline_btn:
    st.sidebar.info("Capturing baseline...")
    total = min(len(FO_SYMBOLS), int(scan_limit))
    captured = 0
    for sym in FO_SYMBOLS[:total]:
        data = fetch_option_chain(sym)
        if not data or "records" not in data:
            time.sleep(per_call_delay)
            continue
        rec = data["records"]
        underlying = rec.get("underlyingValue", None)
        rows = rec.get("data", [])
        if not rows: continue
        strikes = sorted({r.get('strikePrice') for r in rows})
        step = 50
        if len(strikes)>1:
            try: step = int(pd.Series(np.diff(strikes)).mode()[0])
            except: step=50
        atm = nearest_strike(underlying, step)
        targets = [atm, max(0, atm-step)]
        for r in rows:
            sp = r.get('strikePrice')
            expd = r.get('expiryDate', None) or rec.get('expiryDates',[None])[0]
            if expiry_choice != "ALL" and expd != expiry_choice: continue
            if sp not in targets: continue
            for t in ['CE','PE']:
                if t in r and r[t]:
                    key = (sym.upper(), int(sp), t.upper())
                    st.session_state.baseline[key] = float(r[t].get('lastPrice',0) or 0)
                    captured +=1
    st.sidebar.success(f"Baseline captured: {captured} option rows")
    st.session_state.baseline_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ---------------- Layout ----------------
col1, col2 = st.columns([2,1])

# ---------------- Column 1: Volume Spike ----------------
with col1:
    st.header("🔹 Volume Spike Scanner")
    run_main = st.button("▶ Run Volume Spike Scan")
    if run_main:
        total = min(len(FO_SYMBOLS), int(scan_limit))
        results=[]
        for i, sym in enumerate(FO_SYMBOLS[:total]):
            data = fetch_option_chain(sym)
            if not data or "records" not in data: 
                time.sleep(per_call_delay)
                continue
            rec = data["records"]
            underlying = rec.get("underlyingValue",None)
            rows = rec.get("data", [])
            if not rows: continue
            df_rows = [r for r in rows if expiry_choice=="ALL" or r.get("expiryDate",None)==expiry_choice]
            if not df_rows: continue
            strikes = sorted({r.get('strikePrice') for r in df_rows})
            step=50
            if len(strikes)>1:
                try: step=int(pd.Series(np.diff(strikes)).mode()[0])
                except: step=50
            atm=nearest_strike(underlying,step)
            targets=[atm,max(0,atm-step)]
            flat=[r[t].get('totalTradedVolume',0) for r in df_rows for t in ['CE','PE'] if t in r and r[t]]
            med_vol = np.nanmedian([v for v in flat if v>0]) or 1
            now_ts=datetime.now().strftime("%H:%M:%S")
            for r in df_rows:
                sp=r.get('strikePrice')
                if sp not in targets: continue
                for t in ['CE','PE']:
                    if t in r and r[t]:
                        d=r[t]
                        vol=int(d.get('totalTradedVolume') or 0)
                        ltp=float(d.get('lastPrice') or 0)
                        change=float(d.get('change') or 0)
                        oi=int(d.get('openInterest') or 0)
                        vol_ratio = vol/med_vol if med_vol else 0
                        if vol_ratio>=vol_multiplier:
                            results.append({
                                "Symbol": sym,"Expiry": r.get('expiryDate') or rec.get('expiryDates',[None])[0],
                                "Strike": sp,"Type": t,"LTP":round(ltp,2),"Change":round(change,2),
                                "Vol":vol,"OI":oi,"VolRatio":round(vol_ratio,3),"Time":now_ts
                            })
            time.sleep(per_call_delay)
        if results:
            df_results=pd.DataFrame(results).sort_values(by="VolRatio",ascending=False).head(int(top_n_main))
            st.dataframe(df_results,use_container_width=True)
            st.download_button("📥 Download Volume Spike CSV", data=df_results.to_csv(index=False).encode(), file_name="volume_spike_results.csv", mime="text/csv")
        else:
            st.warning("No spikes found.")

# ---------------- Column 2: Top Premium Gainers ----------------
with col2:
    st.header("🚀 Top Premium Gainers")
    if st.session_state.baseline:
        st.success(f"Baseline rows: {len(st.session_state.baseline)} (captured: {st.session_state.baseline_time})")
    else:
        st.info("No baseline. Capture baseline or upload CSV first.")
    run_gainers=st.button("▶ Run Top Premium Gainers")
    if run_gainers:
        total=min(len(FO_SYMBOLS),int(scan_limit))
        gainers=[]
        for sym in FO_SYMBOLS[:total]:
            data = fetch_option_chain(sym)
            if not data or "records" not in data:
                time.sleep(per_call_delay)
                continue
            rec = data["records"]
            underlying = rec.get("underlyingValue",None)
            rows = rec.get("data", [])
            if not rows: continue
            df_rows = [r for r in rows if expiry_choice=="ALL" or r.get("expiryDate",None)==expiry_choice]
            if not df_rows: continue
            strikes = sorted({r.get('strikePrice') for r in df_rows})
            step=50
            if len(strikes)>1:
                try: step=int(pd.Series(np.diff(strikes)).mode()[0])
                except: step=50
            atm=nearest_strike(underlying,step)
            targets=[atm,max(0,atm-step)]
            now_ts=datetime.now().strftime("%H:%M:%S")
            for r in df_rows:
                sp=r.get('strikePrice')
                if sp not in targets: continue
                for t in ['CE','PE']:
                    if t in r and r[t]:
                        if (t=='CE' and not filter_call) or (t=='PE' and not filter_put):
                            continue
                        d=r[t]
                        curr_ltp=float(d.get('lastPrice') or 0)
                        vol=int(d.get('totalTradedVolume') or 0)
                        key=(sym.upper(),int(sp),t.upper())
                        base_ltp = st.session_state.baseline.get(key,None)
                        if base_ltp is None: continue
                        pct_gain=compute_premium_pct(curr_ltp,base_ltp)
                        gainers.append({
                            "Symbol": sym,"Expiry": r.get('expiryDate') or rec.get('expiryDates',[None])[0],
                            "Strike": sp,"Type":t,"BaseLTP":round(base_ltp,2),"CurrLTP":round(curr_ltp,2),
                            "%Gain":round(pct_gain,2),"Vol":vol,"Time":now_ts
                        })
            time.sleep(per_call_delay)
        if gainers:
            df_g=pd.DataFrame(gainers).sort_values(by="%Gain",ascending=False).head(int(top_n_gainers))
            st.dataframe(df_g,use_container_width=True)
            st.download_button("📥 Download Top Premium Gainers CSV", data=df_g.to_csv(index=False).encode(), file_name="top_premium_gainers.csv", mime="text/csv")
        else:
            st.warning("No gainers found.")

st.markdown("---")
st.caption("Notes: Expiry filter applies if option-chain rows include expiry. Increase per_call_delay if NSE blocks requests.")
