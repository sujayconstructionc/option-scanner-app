import streamlit as st
import pandas as pd
import time
from nsepython import nse_optionchain_scrapper

# -------------------- Page Setup --------------------
st.set_page_config(page_title="Live NSE Option Scanner", layout="wide")
st.title("⚡ NSE Live F&O Option Scanner (Auto Refresh + Filters)")
st.caption("Developed for personal live option data scanning")

# -------------------- Sidebar Controls --------------------
with st.sidebar:
    st.header("⚙️ Scanner Settings")
    symbol = st.selectbox("Select Stock", ["RELIANCE", "INFY", "HDFCBANK", "TCS", "ICICIBANK", "SBIN", "LT", "AXISBANK"])
    expiry = st.text_input("Expiry Month (e.g. 28NOV2024)", "28NOV2024")
    volume_mult = st.slider("Volume Multiplier", 1, 20, 5)
    refresh_time = st.slider("Auto Refresh (seconds)", 10, 120, 30)
    auto_refresh = st.checkbox("🔁 Auto Refresh ON", value=True)

# -------------------- Function: Fetch Option Data --------------------
def get_live_option_data(symbol):
    try:
        data = nse_optionchain_scrapper(symbol)
        ce_data = pd.DataFrame(data["records"]["data"])
        ce = pd.json_normalize(ce_data["CE"].dropna())
        pe = pd.json_normalize(ce_data["PE"].dropna())

        ce["type"] = "CE"
        pe["type"] = "PE"

        df = pd.concat([ce, pe])
        df = df[
            [
                "strikePrice",
                "type",
                "lastPrice",
                "change",
                "totalTradedVolume",
                "openInterest",
                "changeinOpenInterest",
            ]
        ]
        df.columns = ["Strike", "Type", "LTP", "%Change", "Volume", "OI", "OI Change"]
        df = df.sort_values(by=["Strike", "Type"]).reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"❌ Error fetching live data: {e}")
        return pd.DataFrame()

# -------------------- Live Display Function --------------------
def display_data():
    df = get_live_option_data(symbol)
    if not df.empty:
        df_filtered = df[df["Volume"] > (df["Volume"].mean() * volume_mult)]
        st.success(f"✅ Live data for {symbol} | Expiry: {expiry}")
        st.dataframe(df_filtered, use_container_width=True)

        # download button with unique key to prevent duplicate ID error
        csv = df_filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download CSV",
            data=csv,
            file_name=f"{symbol}_options.csv",
            mime="text/csv",
            key=f"download_{time.time()}",  # unique key each refresh
        )
    else:
        st.warning("⚠️ No live data received. Try again.")

# -------------------- Main Logic --------------------
placeholder = st.empty()

if auto_refresh:
    while True:
        with placeholder.container():
            display_data()
            st.info(f"🔁 Auto-refreshing every {refresh_time} seconds...")
        time.sleep(refresh_time)
else:
    if st.button("🔄 Get Live Data"):
        with placeholder.container():
            display_data()
