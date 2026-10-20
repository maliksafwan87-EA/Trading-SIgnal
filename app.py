"""
Streamlit Trading Signals App
Shows Buy/Sell/Neutral per asset and 4 timeframes with reasons, chart, TP/SL outcome, and POC.
Data: live (biquote) for forex/metals, yfinance for stocks.

Mobile-optimized layout.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from engine import (
    fetch_ohlc, add_indicators, generate_signal,
    check_outcome, compute_poc, normalize_symbol
)
from datetime import datetime

st.set_page_config(
    page_title="Signals",
    layout="centered",          # better for mobile
    page_icon="📈",
    initial_sidebar_state="collapsed"
)

st.title("📈 Signals")
st.caption("Forex • Metals • Stocks")

# --- Top controls (always visible on mobile) ---
col_a, col_b = st.columns([3, 1])
with col_a:
    asset = st.text_input(
        "Symbol",
        value="XAUUSD",
        help="XAUUSD, EURUSD, AAPL, TSLA, GC=F …",
        label_visibility="collapsed",
        placeholder="Enter symbol (e.g. XAUUSD)"
    ).strip().upper()
with col_b:
    refresh = st.button("🔄", type="primary", use_container_width=True, help="Refresh data")

auto = st.checkbox("Auto-refresh every 60s", value=False)

with st.expander("Supported symbols & data notes"):
    st.markdown("""
    **Metals:** XAUUSD, XAGUSD, GOLD  
    **Forex:** EURUSD, GBPUSD, USDJPY, …  
    **Stocks:** AAPL, MSFT, TSLA, …  

    • Forex & Metals → live mid prices (biquote.io, tick volume)  
    • Stocks → yfinance (near real-time or ~15 min delay, real volume)
    """)

if not asset:
    st.warning("Enter an asset symbol.")
    st.stop()

provider_sym, asset_class = normalize_symbol(asset)
st.subheader(f"{asset}  •  {asset_class.replace('_', ' ').title()}")

# Cache
if "signals" not in st.session_state or refresh or auto:
    st.session_state.signals = {}
    st.session_state.dfs = {}

TIMEFRAMES = ["5m", "15m", "1h", "4h"]
TF_LABELS = {"5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h"}

# Fetch
progress = st.progress(0)
for i, tf in enumerate(TIMEFRAMES):
    with st.spinner(f"Loading {tf}…"):
        df = fetch_ohlc(asset, tf, limit=120)
        if not df.empty:
            df = add_indicators(df)
            sig = generate_signal(df)
            outcome = check_outcome(df, sig)
            poc = compute_poc(df)
            st.session_state.dfs[tf] = df
            st.session_state.signals[tf] = {**sig, "outcome": outcome, "poc": poc}
        else:
            st.session_state.signals[tf] = {
                "signal": "Neutral", "reasons": ["No data"],
                "entry": None, "tp": None, "sl": None, "outcome": "N/A", "poc": None,
                "price": None, "confidence": 0
            }
    progress.progress((i + 1) / len(TIMEFRAMES))
progress.empty()

# Summary cards — 2×2 on mobile
st.markdown("### Signals")
cols = st.columns(2)
for idx, tf in enumerate(TIMEFRAMES):
    sig = st.session_state.signals.get(tf, {})
    signal = sig.get("signal", "Neutral")
    color = {"Buy": "#16a34a", "Sell": "#dc2626", "Neutral": "#6b7280"}[signal]
    outcome = sig.get("outcome", "N/A")
    with cols[idx % 2]:
        st.markdown(
            f"""
            <div style="border:1px solid #e5e7eb; border-radius:12px; padding:12px; margin-bottom:8px; text-align:center;">
                <div style="font-weight:600;">{TF_LABELS[tf]}</div>
                <div style="font-size:1.4rem; color:{color}; margin:4px 0;">{signal}</div>
                <div style="font-size:0.85rem; color:#6b7280;">
                    {sig.get('confidence', 0)}% · {outcome}<br>
                    {f"{sig.get('price', ''):.5g}" if sig.get('price') else ""}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

# Timeframe selector
selected_tf = st.selectbox(
    "Detail view",
    TIMEFRAMES,
    format_func=lambda x: TF_LABELS[x]
)

sig = st.session_state.signals.get(selected_tf, {})
df = st.session_state.dfs.get(selected_tf)

# Chart (full width, shorter height for phones)
st.markdown(f"### Chart — {TF_LABELS[selected_tf]}")
if df is not None and not df.empty:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        row_heights=[0.72, 0.28])
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="Price", increasing_line_color="#26a69a", decreasing_line_color="#ef5350"
    ), row=1, col=1)
    if "EMA20" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["EMA20"], name="EMA20", line=dict(color="orange", width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], name="EMA50", line=dict(color="royalblue", width=1.5)), row=1, col=1)

    if sig.get("signal") in ("Buy", "Sell") and sig.get("entry"):
        color = "#16a34a" if sig["signal"] == "Buy" else "#dc2626"
        fig.add_trace(go.Scatter(
            x=[df.index[-1]], y=[sig["entry"]],
            mode="markers", marker=dict(size=14, color=color, symbol="triangle-up" if sig["signal"]=="Buy" else "triangle-down"),
            name=sig["signal"]
        ), row=1, col=1)
        if sig.get("tp"):
            fig.add_hline(y=sig["tp"], line_dash="dash", line_color="#16a34a", annotation_text="TP", row=1, col=1)
        if sig.get("sl"):
            fig.add_hline(y=sig["sl"], line_dash="dash", line_color="#dc2626", annotation_text="SL", row=1, col=1)

    if sig.get("poc"):
        fig.add_hline(y=sig["poc"], line_dash="dot", line_color="purple", annotation_text="POC", row=1, col=1)

    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color="rgba(120,120,120,0.4)"), row=2, col=1)
    fig.update_layout(
        height=480,
        xaxis_rangeslider_visible=False,
        showlegend=False,
        margin=dict(l=8, r=8, t=20, b=8),
        font=dict(size=11)
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No chart data for this timeframe.")

# Signal details in expander
with st.expander(f"Signal details — {TF_LABELS[selected_tf]}", expanded=True):
    signal = sig.get("signal", "Neutral")
    st.markdown(f"**Signal:** <span style='color:{'#16a34a' if signal=='Buy' else '#dc2626' if signal=='Sell' else '#6b7280'}'>{signal}</span> · {sig.get('confidence', 0)}%", unsafe_allow_html=True)
    st.markdown(f"**Outcome:** {sig.get('outcome', 'N/A')}")
    if sig.get("entry"):
        st.write(f"**Entry:** {sig['entry']}")
        st.write(f"**TP:** {sig.get('tp', '—')}  |  **SL:** {sig.get('sl', '—')}")
        st.write(f"**ATR:** {sig.get('atr', '—')}")
    if sig.get("poc"):
        st.write(f"**POC:** {sig['poc']}")

    st.markdown("**Reasons**")
    for r in sig.get("reasons", []):
        st.markdown(f"• {r}")

# Compact summary table
with st.expander("All timeframes"):
    rows = []
    for tf in TIMEFRAMES:
        s = st.session_state.signals.get(tf, {})
        rows.append({
            "TF": TF_LABELS[tf],
            "Signal": s.get("signal"),
            "Price": s.get("price"),
            "Outcome": s.get("outcome"),
            "Conf": s.get("confidence")
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.caption(f"Updated {datetime.now().strftime('%H:%M:%S')} · engine.py")

if auto:
    import time
    time.sleep(60)
    st.rerun()
