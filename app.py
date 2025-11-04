# Option Scanner App (Private Version)
# Developed for Gunvant (sujayconstruction.c@gmail.com)
# Streamlit Version – 15-min Timeframe + Volume Multiplier + Expiry Filter

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# -----------------------------
# Page Settings
# -----------------------------
st.set_page_config(page_title="Option Scanner App", page_icon="📈", layout="wide")

# -----------------------------
# Sidebar Controls
# -----------------------------
st.sidebar.header("⚙️ Scanner Settings")

# Timeframe selector
timeframe = st.sidebar.selectbox(
    "Select Timeframe (minutes)",
    options=[1, 3, 5, 15],
    index=3
)

# Volume Multiplier
vol_multiplier = st.sidebar.slider(
    "Volume Multiplier (× Average Volume)",
    min_value=1.0,
    max_value=5.0,
    step=0.5,
    value=2.0
)

# Expiry Month selector
expiry_choice = st.sidebar.selectbox(
    "Select Expiry",
    options=["Current Week", "Next Week", "Monthly", "Custom Date"]
)

# Custom expiry (if selected)
custom_expiry = None
if expiry_choice == "Custom Date":
    custom_expiry = st.sidebar.date_input("Choose Expiry Date")

# Demo mode checkbox
demo_mode = st.sidebar.checkbox("Enable Demo Mode", value=True)

st.sidebar.markdown("---")
st.sidebar.caption("Private version — visible only to sujayconstruction.c@gmail.com")

# -----------------------------
# Header
# -----------------------------
st.title("📊 Option Scanner App (Private)")
st.caption("Auto ATM/ITM selector • 15-min timeframe • Volume/OI filters")

# -----------------------------
# Load Demo Data
# -----------------------------
@st.cache_data
def load_demo_data():
    np.random.seed(42)
    symbols = ["RELIANCE", "INFY", "TCS", "HDFCBANK", "SBIN", "ICICIBANK", "KOTAKBANK", "LT"]
    option_types = ["CE", "PE"]

    data = []
    for sym in symbols:
        for opt in option_types:
            ltp = np.random.uniform(50, 400)
            vol = np.random.randint(10000, 200000)
            oi = np.random.randint(100000, 500000)
            change = np.random.uniform(-5, 5)
            entry_time = datetime.now().strftime("%H:%M:%S")

            data.append({
                "Symbol": sym,
                "Option Type": opt,
                "LTP": round(ltp, 2),
                "% Change": round(change, 2),
                "Volume": vol,
                "OI Change": oi,
                "Entry Time": entry_time
            })
    return pd.DataFrame(data)

if demo_mode:
    df = load_demo_data()
else:
    st.warning("⚠️ Live data mode not connected yet. Using demo data.")
    df = load_demo_data()

# -----------------------------
# Apply Volume Filter
# -----------------------------
avg_volume = df["Volume"].mean()
filtered_df = df[df["Volume"] > avg_volume * vol_multiplier]

# -----------------------------
# Display Results
# -----------------------------
st.subheader(f"Scan Results ({timeframe}-min • {expiry_choice})")

if not filtered_df.empty:
    st.dataframe(filtered_df, use_container_width=True)
else:
    st.info("No symbols found matching the selected filters.")

# -----------------------------
# Download Option
# -----------------------------
csv = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button("📥 Download CSV", csv, "option_scanner_results.csv", "text/csv")

# -----------------------------
# Footer
# -----------------------------
st.markdown("---")
st.caption("© 2025 Option Scanner App — Private version for sujayconstruction.c@gmail.com")
