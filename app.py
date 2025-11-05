# app.py
# NSE F&O ATM/-1 ITM Option Scanner — Auto Symbol List + Volume & Premium Spike
import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime
from nsepython import nse_optionchain_scrapper, nse_eq_symbol_list
import math

st.set_page_config(page_title="Full F&O Option Scanner", layout="wide")
st.title("💥 Full F&O ATM & -1 ITM Option Scanner — Volume + Premium Spike")

st.caption("Automatically scans all F&O stocks for ATM & -1 ITM option strikes with volume and premium analysis.")

# ---------------- Sidebar controls ----------------
with st.sidebar:
    st.header("Scanner Settings")
    expiry_text = st.text_input("Expiry Month (e.g. 28NOV2024)", value="")
    timeframe = st.selectbox("Timeframe (label only)", ["1m", "5m", "15m"], index=2)
    vol_multiplier = st.number_input("Volume Spike Multiplier", 1.0, 20.0, 2.0, 0.1)
    scan_limit = st.number_input("Number of F&O stocks to scan (max 200+)", 5, 250, 50, 5)
    delay = st.number_input("Delay between requests (sec)", 0.5, 5.0, 1.0, 0.1)
    top_n = st.number_input("Show Top N Results", 5, 100, 25, 1)
    st.markdown("---")
    st.caption("💡 You can increase scan limit later to include all 200+ stocks.")

def nearest_strike(price, step=50):
    return int(round(price / step) * step)

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

def get_all_fo_symbols():
    df = nse_eq_symbol_list()
    fo_list = df[df["series"] == "EQ"]["symbol"].unique().tolist()
    fo_list.sort()
    return fo_list

@st.cache_data(ttl=3600)
def fetch_and_process(sym, vol_multiplier):
    try:
        raw = nse_optionchain_scrapper(sym)
    except Exception as e:
        return []

    rec = raw.get("records", {})
    underlying = rec.get("underlyingValue", None)
    rows = rec.get("data", [])
    if not rows:
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
        mode = pd.Series(diffs).mode().iloc[0]
        if mode > 0: step = mode

    atm = nearest_strike(underlying, step)
    target = [atm, atm - step]
    med_vol = df["Volume"].replace(0, np.nan).median() or 1

    candidates = []
    now = datetime.now().strftime("%H:%M:%S")
    for ts in target:
        part = df[df["Strike"] == ts]
        for _, r in part.iterrows():
            ltp = float(r["LTP"])
            change = float(r["Change"])
            vol = float(r["Volume"])
            prem = compute_premium_pct(ltp, change)
            v_ratio = safe_div(vol, med_vol)
            score = v_ratio * (1 + prem / 100)
            if v_ratio >= vol_multiplier:
                candidates.append({
                    "Symbol": sym,
                    "Strike": ts,
                    "Type": r["Type"],
                    "LTP": round(ltp,2),
                    "Premium%": round(prem,2),
                    "Vol": int(vol),
                    "VolRatio": round(v_ratio,2),
                    "OI": int(r["OI"]),
                    "OIChg": int(r["OI Change"]),
                    "Score": round(score,2),
                    "Time": now
                })
    return candidates

# ---------------- Scan run ----------------
if st.button("🚀 Run Full F&O Scan"):
    st.info("Fetching all F&O symbols, please wait...")
    fo_symbols = get_all_fo_symbols()
    st.success(f"Total F&O symbols found: {len(fo_symbols)}")

    results = []
    prog = st.progress(0)
    total = min(len(fo_symbols), int(scan_limit))
    for i, sym in enumerate(fo_symbols[:total]):
        with st.spinner(f"Scanning {sym} ({i+1}/{total})..."):
            res = fetch_and_process(sym, vol_multiplier)
            results.extend(res)
            prog.progress(int((i+1)/total*100))
            time.sleep(delay)

    if not results:
        st.warning("No matches found (try lower volume multiplier).")
    else:
        df = pd.DataFrame(results)
        df = df.sort_values(by="Score", ascending=False).reset_index(drop=True)
        top = df.head(int(top_n))
        st.subheader(f"Top {len(top)} Option Spikes (ATM & ITM)")
        st.dataframe(top, use_container_width=True)
        csv = top.to_csv(index=False).encode()
        st.download_button("📥 Download CSV", csv, "fo_option_scanner.csv", mime="text/csv")
