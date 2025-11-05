import streamlit as st
import pandas as pd
from nsepython import nse_optionchain_scrapper

st.set_page_config(page_title="Live F&O Option Scanner", layout="wide")

st.title("⚡ NSE Live F&O Option Scanner")

st.markdown("Use this app to view **real-time option chain data** for F&O stocks.")

# ----------------- Stock Selection -----------------
symbol = st.selectbox(
    "Select F&O Stock Symbol 👇",
    ["RELIANCE", "INFY", "HDFCBANK", "TCS", "ICICIBANK", "SBIN", "LT", "AXISBANK"],
)

# ----------------- Live Data Function -----------------
def get_live_option_data(symbol):
    try:
        data = nse_optionchain_scrapper(symbol, "latest")
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
        return df
    except Exception as e:
        st.error(f"❌ Error fetching live data: {e}")
        return pd.DataFrame()

# ----------------- Fetch Button -----------------
if st.button("🔄 Get Live Data"):
    with st.spinner("Fetching latest option data..."):
        df = get_live_option_data(symbol)
        if not df.empty:
            st.success("✅ Live data connected successfully!")
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("⚠️ No data received, try again later.")
else:
    st.info("👆 Select a stock and click the button to fetch live data.")
