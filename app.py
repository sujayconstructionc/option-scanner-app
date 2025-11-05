import streamlit as st
import pandas as pd
from nsepython import nse_optionchain_scrapper

# -------------------- Page Config --------------------
st.set_page_config(page_title="Live NSE Option Scanner", layout="wide")

st.title("⚡ NSE Live F&O Option Scanner")
st.markdown("Get real-time **Option Chain data** directly from NSE in one click.")

# -------------------- Stock Selection --------------------
symbol = st.selectbox(
    "Select F&O Stock Symbol 👇",
    ["RELIANCE", "INFY", "HDFCBANK", "TCS", "ICICIBANK", "SBIN", "LT", "AXISBANK"],
)

# -------------------- Function to Fetch Live Data --------------------
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

# -------------------- Fetch Button --------------------
if st.button("🔄 Get Live Data"):
    with st.spinner("Fetching latest option data..."):
        df = get_live_option_data(symbol)
        if not df.empty:
            st.success("✅ Live data connected successfully!")
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download CSV", data=csv, file_name=f"{symbol}_options.csv", mime="text/csv")
        else:
            st.warning("⚠️ No data received, try again later.")
else:
    st.info("👆 Select a stock and click 'Get Live Data' to start scanning.")
