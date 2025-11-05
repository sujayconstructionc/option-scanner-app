import streamlit as st
import pandas as pd
import datetime
import time
from nsepython import nse_optionchain_scrapper

st.set_page_config(page_title="Full F&O Option Scanner", layout="wide")

st.title("📊 F&O Option Scanner — Live + Top 15 Premium Gainers")

# ---- Sidebar ----
st.sidebar.header("⚙️ Scanner Settings")
expiry = st.sidebar.text_input("Expiry (e.g. 28NOV2024)", "28NOV2024")
refresh_interval = st.sidebar.slider("Auto Refresh (seconds)", 30, 300, 60)

# ---- Global Variables ----
if "baseline_data" not in st.session_state:
    st.session_state.baseline_data = {}

# ---- F&O Stocks ----
fo_stocks = [
    "RELIANCE","HDFCBANK","ICICIBANK","INFY","SBIN","TCS","AXISBANK","LT","KOTAKBANK",
    "HINDUNILVR","ITC","BAJFINANCE","ADANIENT","ADANIPORTS","MARUTI","SUNPHARMA","TITAN",
    "ULTRACEMCO","POWERGRID","NESTLEIND","ONGC","TATAMOTORS","NTPC","JSWSTEEL","TATASTEEL",
    "BHARTIARTL","WIPRO","GRASIM","BPCL","EICHERMOT","CIPLA","BRITANNIA","HCLTECH",
    "DRREDDY","COALINDIA","BAJAJFINSV","HDFCLIFE","HEROMOTOCO","TECHM","SBILIFE",
    "DIVISLAB","HINDALCO","INDUSINDBK","UPL","TATACONSUM","APOLLOHOSP","BAJAJ-AUTO",
    "ICICIPRULI","ADANIGREEN","DLF","TORNTPHARM","PIDILITIND","SHREECEM","M&M","TRENT",
    "AMBUJACEM","ADANIPOWER","BANKBARODA","VEDL","GAIL","INDIGO","BEL","BANDHANBNK",
    "PNB","COLPAL","CANBK","IDFCFIRSTB","PAYTM","ZOMATO","TATAPOWER","ACC","GODREJCP",
    "UBL","TVSMOTOR","IOC","HINDPETRO","POLYCAB","IRCTC","CHOLAFIN","INDHOTEL","AUROPHARMA",
    "TATACHEM","ASHOKLEY","BIOCON","BOSCHLTD","RECLTD","NMDC","PFC","ABB","OFSS","LUPIN",
    "CONCOR","MFSL","NAUKRI","CUMMINSIND","HAVELLS","SRF","JINDALSTEL","PIIND","PAGEIND",
    "PETRONET","ALKEM","MPHASIS","BHEL","MOTHERSON","GUJGASLTD","ATUL","COFORGE",
    "AUBANK","SIEMENS","INDIAMART","GLENMARK","MUTHOOTFIN","GRANULES","SYNGENE","COROMANDEL",
    "VOLTAS","IRFC","EXIDEIND","PERSISTENT","ESCORTS","OBEROIRLTY","ADANITRANS","ABBOTINDIA",
    "NAVINFLUOR","LTIM","ZYDUSLIFE","HONAUT","DELHIVERY","IDFC","INDUSTOWER","POLICYBZR",
    "LALPATHLAB","TATACOMM","HAL","KPITTECH","BALRAMCHIN","HDFCAMC","DIXON","3MINDIA",
    "PNCINFRA","RAJESHEXPO","CROMPTON","GMRINFRA","TATAMTRDVR","BATAINDIA","CANFINHOME",
    "BERGEPAINT","TORNTPOWER","SUNTV","JUBLFOOD","FEDERALBNK","IRB","ASTRAL","SRTRANSFIN",
    "ABFRL","PEL","IDBI","NHPC","TATAELXSI","LICHSGFIN","DEEPAKNTR","DALBHARAT","CGPOWER",
    "UNIONBANK","HINDCOPPER","LTTS","LAURUSLABS","SAIL","RVNL","BANKINDIA","BALKRISIND",
    "ONGC","IOB","CUB","TATATECH","NBCC","NMDC","METROPOLIS","NAM-INDIA","RBLBANK",
    "HUDCO","IRCON","FINCABLES","BSOFT"
]

# ---- Helper Function ----
def fetch_option_data(symbol):
    try:
        data = nse_optionchain_scrapper(symbol)
        df = pd.DataFrame(data["records"]["data"])
        ce = df[df["CE"].notna()]["CE"][["strikePrice", "lastPrice", "openInterest", "totalTradedVolume"]]
        pe = df[df["PE"].notna()]["PE"][["strikePrice", "lastPrice", "openInterest", "totalTradedVolume"]]
        ce["type"] = "CE"
        pe["type"] = "PE"
        df_all = pd.concat([ce, pe])
        df_all["symbol"] = symbol
        return df_all
    except Exception:
        return pd.DataFrame()

# ==============================================
# 🟢 SECTION 1: LIVE OPTION SCANNER
# ==============================================
st.subheader("📈 Live Option Scanner (Manual Symbol)")

symbol = st.selectbox("Select F&O Stock", sorted(fo_stocks))
if st.button("🔍 Fetch Live Data"):
    df = fetch_option_data(symbol)
    if not df.empty:
        df["%Change"] = df["lastPrice"].pct_change() * 100
        df["Time"] = datetime.datetime.now().strftime("%H:%M:%S")
        st.dataframe(df[["Time","symbol","type","strikePrice","lastPrice","openInterest","totalTradedVolume"]])
        st.success("✅ Live Option Data Fetched!")
    else:
        st.warning("⚠️ Unable to fetch data. Try again later.")

# ==============================================
# 🟠 SECTION 2: TOP 15 PREMIUM GAINERS
# ==============================================
st.subheader("🚀 Top 15 Premium Gainers (9:15 → Now)")

# ---- 9:15 Baseline Capture ----
if st.button("📸 Capture 9:15 Baseline Snapshot"):
    for sym in fo_stocks:
        df = fetch_option_data(sym)
        if not df.empty:
            st.session_state.baseline_data[sym] = df
    st.success("✅ 9:15 Baseline Captured Successfully!")

# ---- Live Market Scan ----
if st.button("🔥 Run Full Market Scan"):
    all_results = []
    for sym in fo_stocks:
        live_df = fetch_option_data(sym)
        base_df = st.session_state.baseline_data.get(sym, pd.DataFrame())
        if not live_df.empty and not base_df.empty:
            merged = pd.merge(
                live_df, base_df, on=["strikePrice", "type"], suffixes=("_now", "_915")
            )
            merged["%Gain"] = (
                (merged["lastPrice_now"] - merged["lastPrice_915"]) / merged["lastPrice_915"]
            ) * 100
            merged["symbol"] = sym
            merged["timestamp"] = datetime.datetime.now().strftime("%H:%M:%S")
            all_results.append(merged)
        time.sleep(0.5)

    if all_results:
        final = pd.concat(all_results)
        final = final.sort_values(by="%Gain", ascending=False).head(15)
        st.dataframe(final[["timestamp","symbol","type","strikePrice","%Gain"]])
        st.success("✅ Top 15 Premium Gainers Displayed!")
    else:
        st.warning("⚠️ Capture 9:15 snapshot first!")

st.info("💡 Tip: Capture baseline at 9:15 AM once, then re-run market scan anytime.")
