import streamlit as st

from stock_watcher import MAX_SYMBOLS, analyze_symbols, parse_symbols, score_key

st.set_page_config(page_title="Stock Momentum Monitor", layout="wide")
st.title("Stock Momentum Monitor")
st.caption("Moving-average and volume-based STAY/TRIM/CUT scanner")

symbols_text = st.text_input("Symbols (comma-separated, max 20)", "NVDA,AMD,SMCI")
period = st.selectbox("History Period", ["6mo", "1y", "2y"], index=1)
weak_sector = st.checkbox("Sector weak simultaneously")
weak_earnings = st.checkbox("Weak earnings reaction")

if st.button("Run Analysis"):
    try:
        symbols = parse_symbols(symbols_text)
        st.info(f"Monitoring {len(symbols)} symbol(s). Max allowed: {MAX_SYMBOLS}.")
        results = analyze_symbols(symbols, period, weak_sector, weak_earnings)
        st.dataframe(results, use_container_width=True)
        st.markdown(f"**Score Key:** `{score_key()}`")
    except Exception as exc:
        st.error(str(exc))
