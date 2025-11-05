# app.py
# Full F&O ATM/-1 ITM scanner — volume spike + premium gainer — Streamlit
# Requirements: streamlit, pandas, nsepython, requests (if using Telegram)
# Paste this into your repo's app.py and deploy / rerun on Streamlit Cloud.

import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime
from nsepython import nse_optionchain_scrapper
import math
import requests

st.set_page_config(page_title="F&O ATM/ITM Scanner", layout="wide")
st.title("⚡ F&O ATM & -1 ITM Scanner — Volume Spike + Premium Gainers")

st.markdown(
    "Scan a list of F&O symbols for ATM and -1 ITM strikes, detect volume spikes and premium gainers, rank results."
)
st.caption(
    "Note: This uses NSE option-chain snapshots (nsepython). Use moderate scan limits and delay to avoid rate limits."
)

# ---------------- Sidebar controls ----------------
with st.sidebar:
    st.header("Scanner Controls")
    st.markdown("Paste symbols (one per line). Example: RELIANCE")
    symbols_input = st.text_area(
        "Symbols (one per line)",
        value="RELIANCE\nINFY\nTCS\nHDFCBANK\nICICIBANK\nSBIN\nLT\nAXISBANK",
        height=150,
    )
    timeframe = st.selectbox(
        "Timeframe (informational)",
        options=["1m", "5m", "15m"],
        index=2,
        help="This is informational. Option chain is a snapshot — timeframe matters if you compare intraday candles from another source."
    )
    expiry_text = st.text_input("Expiry (optional, e.g. 28NOV2024 or leave blank)", value="")
    vol_multiplier = st.number_input(
        "Volume multiplier threshold (relative to median chain volume)",
        min_value=0.1,
        max_value=20.0,
        value=2.0,
        step=0.1,
    )
    scan_limit = st.number_input(
        "Max symbols per run (set to lower if testing)",
        min_value=1,
        max_value=500,
        value=50,
        step=1,
    )
    per_call_delay = st.number_input(
        "Delay between API calls (seconds) — recommended 0.8–2.0",
        min_value=0.1,
        max_value=10.0,
        value=1.0,
        step=0.1,
    )
    top_n = st.number_input("Show top N results", min_value=1, max_value=200, value=30, step=1)
    auto_refresh = st.checkbox("Auto-refresh every N seconds (danger: heavy API use)", value=False)
    refresh_seconds = st.number_input("Auto-refresh interval (s)", min_value=10, max_value=3600, value=60, step=5)
    st.markdown("---")
    st.subheader("Telegram Alerts (optional)")
    use_telegram = st.checkbox("Enable Telegram alerts for top results", value=False)
    bot_token = st.text_input("Bot token (if enabling Telegram)")
    chat_id = st.text_input("Chat ID (if enabling Telegram)")
    st.caption("Enable only if you know your bot token & chat id. Alerts will contain top N items summary.")


def nearest_strike(price, step=50):
    # safe rounding to nearest strike step
    if price is None or math.isnan(price):
        return None
    return int(round(price / step) * step)


def safe_div(a, b):
    try:
        return a / b if b != 0 else 0
    except Exception:
        return 0


def compute_premium_pct(ltp, change):
    # percent change relative to previous close = change / (ltp - change)
    prev = ltp - change
    if prev and prev != 0:
        return (change / prev) * 100.0
    return 0.0


def fetch_and_process_symbol(sym, vol_mult_threshold, expiry_label=""):
    """
    Returns list of candidate dicts for ATM and -1 ITM strikes for this symbol.
    """
    try:
        raw = nse_optionchain_scrapper(sym)
    except Exception as e:
        return {"error": f"API error for {sym}: {e}", "candidates": []}

    # records->data is list of strike rows; underlyingValue is spot
    records = raw.get("records", {})
    underlying = records.get("underlyingValue", None)
    data_rows = records.get("data", [])  # list of dicts with keys 'CE' and 'PE' maybe
    if not data_rows:
        return {"error": f"No option-chain data for {sym}", "candidates": []}

    # Build flattened table: each row may contain CE and/or PE
    rows = []
    for r in data_rows:
        strike = r.get("strikePrice")
        ce = r.get("CE")
        pe = r.get("PE")
        if ce:
            rows.append(
                {
                    "Strike": strike,
                    "Type": "CE",
                    "LTP": ce.get("lastPrice", 0),
                    "Change": ce.get("change", 0),
                    "Volume": ce.get("totalTradedVolume", 0) or 0,
                    "OI": ce.get("openInterest", 0) or 0,
                    "OI Change": ce.get("changeinOpenInterest", 0) or 0,
                }
            )
        if pe:
            rows.append(
                {
                    "Strike": strike,
                    "Type": "PE",
                    "LTP": pe.get("lastPrice", 0),
                    "Change": pe.get("change", 0),
                    "Volume": pe.get("totalTradedVolume", 0) or 0,
                    "OI": pe.get("openInterest", 0) or 0,
                    "OI Change": pe.get("changeinOpenInterest", 0) or 0,
                }
            )

    df = pd.DataFrame(rows)
    if df.empty:
        return {"error": f"No CE/PE rows parsed for {sym}", "candidates": []}

    # Detect strike step (mode of diffs)
    strikes_sorted = sorted(df["Strike"].unique())
    if len(strikes_sorted) > 1:
        diffs = np.diff(strikes_sorted)
        # take mode or fallback 50
        try:
            step = int(pd.Series(diffs).mode().iloc[0])
            if step <= 0:
                step = 50
        except Exception:
            step = 50
    else:
        step = 50

    # ATM detection from underlying if available else use nearest to median strike
    if underlying:
        atm = nearest_strike(underlying, step=step)
    else:
        atm = nearest_strike(np.median(strikes_sorted), step=step)

    # targets: ATM and -1 ITM (ATM - step)
    target_strikes = [atm, max(0, atm - step)]
    candidates = []

    # compute median volume of chain for vol spike reference (per type combined)
    median_vol = df["Volume"].replace(0, np.nan).median()
    if pd.isna(median_vol) or median_vol == 0:
        median_vol = df["Volume"].replace(0, np.nan).mean()
    if pd.isna(median_vol) or median_vol == 0:
        median_vol = 1.0  # avoid divide by zero

    # for each target strike, pick CE and PE rows if present
    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for ts in target_strikes:
        df_strike = df[df["Strike"] == ts]
        if df_strike.empty:
            continue
        for _, r in df_strike.iterrows():
            ltp = float(r["LTP"]) if not pd.isna(r["LTP"]) else 0.0
            change = float(r["Change"]) if not pd.isna(r["Change"]) else 0.0
            vol = int(r["Volume"]) if not pd.isna(r["Volume"]) else 0
            oi = int(r["OI"]) if not pd.isna(r["OI"]) else 0
            oi_chg = float(r["OI Change"]) if not pd.isna(r["OI Change"]) else 0.0

            premium_pct = compute_premium_pct(ltp, change)
            vol_ratio = safe_div(vol, median_vol)  # how many times median
            oi_pct = safe_div(oi_chg, max(1, oi)) * 100.0  # % change in OI approx

            # detect spike condition
            is_vol_spike = vol_ratio >= vol_mult_threshold

            # score for ranking: weight volume ratio and premium pct (customizable)
            score = vol_ratio * (1 + premium_pct / 100.0)

            candidates.append(
                {
                    "Symbol": sym,
                    "Expiry": expiry_label or "",
                    "Timeframe": timeframe,
                    "DetectedAt": now_ts,
                    "Strike": ts,
                    "Type": r["Type"],
                    "LTP": ltp,
                    "PremiumChange": round(premium_pct, 3),
                    "Volume": vol,
                    "VolRatio": round(vol_ratio, 3),
                    "OI": oi,
                    "OIChange": oi_chg,
                    "OI%": round(oi_pct, 3),
                    "IsVolSpike": bool(is_vol_spike),
                    "Score": score,
                }
            )

    # Return parsed and candidate list
    return {"error": None, "candidates": candidates, "atm": atm, "step": step, "median_vol": median_vol}


# ---------------- Run scan button / loop ----------------
symbols = [s.strip().upper() for s in symbols_input.splitlines() if s.strip()]
if not symbols:
    st.warning("Please paste at least one symbol in the left sidebar.")
    st.stop()

scan_btn = st.button("🔎 Run Scan Now")
placeholder = st.empty()
progress_bar = st.progress(0)

def send_telegram_summary(bot_token, chat_id, df_top):
    try:
        text = f"Option Scanner Alert — Top {len(df_top)}\n"
        for i, row in df_top.iterrows():
            text += f"{i+1}. {row.Symbol} {row.Strike}{row.Type} Vol:{row.Volume} Prem%:{row.PremiumChange} OI%:{row['OI%']} Time:{row.DetectedAt}\n"
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        r = requests.post(url, data=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        st.warning(f"Telegram send error: {e}")
        return False

def do_scan_run():
    results = []
    total = min(len(symbols), int(scan_limit))
    for idx, sym in enumerate(symbols[:total]):
        with st.spinner(f"Fetching {sym} ({idx+1}/{total}) ..."):
            res = fetch_and_process_symbol(sym, vol_multiplier, expiry_text)
            if res.get("error"):
                # record error row
                results.append({"Symbol": sym, "Error": res["error"]})
            else:
                results.extend(res.get("candidates", []))
        progress = int(((idx+1) / total) * 100)
        progress_bar.progress(progress)
        time.sleep(per_call_delay)  # be polite to NSE
    progress_bar.progress(100)
    return results

# Auto-refresh loop (if enabled)
if auto_refresh:
    st.info(f"Auto-refresh ON — every {refresh_seconds} seconds. Click 'Stop' to cancel.")
    stop_button = st.button("Stop Auto-refresh")
    run_once = True
    # use session state to manage loop
    if "stop_signal" not in st.session_state:
        st.session_state.stop_signal = False
    while True:
        if st.session_state.stop_signal:
            break
        results = do_scan_run()
        df_all = pd.DataFrame(results)
        if not df_all.empty:
            # filter out error rows
            if "Error" in df_all.columns:
                st.write(df_all[df_all["Error"].notna()])
                df_all = df_all[df_all["Error"].isna()]
            # rank by Score and only show vol spike rows by default
            df_rank = df_all.copy()
            df_rank = df_rank.sort_values(by="Score", ascending=False).reset_index(drop=True)
            top = df_rank.head(int(top_n))
            placeholder.dataframe(top, use_container_width=True)
            csv = top.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Top CSV", data=csv, file_name="top_options.csv", key=f"dl_{time.time()}")
            if use_telegram and bot_token and chat_id:
                send_telegram_summary(bot_token, chat_id, top)
        else:
            placeholder.info("No results in this run.")
        # sleep until next refresh or stop
        for i in range(int(refresh_seconds)):
            if st.session_state.stop_signal:
                break
            time.sleep(1)
        # check stop button
        if stop_button:
            st.session_state.stop_signal = True
            break
else:
    if scan_btn:
        results = do_scan_run()
        df_all = pd.DataFrame(results)
        if df_all.empty:
            st.info("No results collected (check symbols or try again).")
        else:
            if "Error" in df_all.columns:
                st.write(df_all[df_all["Error"].notna()])
                df_all = df_all[df_all["Error"].isna()]
            df_rank = df_all.sort_values(by="Score", ascending=False).reset_index(drop=True)
            top = df_rank.head(int(top_n))
            st.subheader(f"Top {len(top)} strikes (by score)")
            st.dataframe(top, use_container_width=True)
            csv = top.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Top CSV", data=csv, file_name="top_options.csv", key=f"dl_{time.time()}")
            if use_telegram and bot_token and chat_id:
                ok = send_telegram_summary(bot_token, chat_id, top)
                if ok:
                    st.success("Telegram alert sent for top items.")
                else:
                    st.warning("Telegram alert failed.")
