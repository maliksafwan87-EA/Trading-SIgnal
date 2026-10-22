"""
SUFX Signals — Premium Mobile-First Streamlit App
"""

import streamlit as st
import plotly.graph_objects as go
from engine import fetch_data, get_signal, check_outcome
import pandas as pd

st.set_page_config(
    page_title="SUFX Signals",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={"Get Help": None, "Report a bug": None, "About": None}
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
}

.stApp {
    background: #f8fafc;
    color: #0f172a;
}

header[data-testid="stHeader"] { background: transparent; }

.stTextInput > div > div > input {
    border-radius: 12px !important;
    border: 1.5px solid #e2e8f0 !important;
    padding: 0.65rem 1rem !important;
    font-size: 15px !important;
    background: white !important;
    transition: all 0.18s ease;
}
.stTextInput > div > div > input:focus {
    border-color: #0f172a !important;
    box-shadow: 0 0 0 3px rgba(15,23,42,0.08) !important;
}

.stButton > button {
    border-radius: 12px !important;
    background: #0f172a !important;
    color: white !important;
    font-weight: 600 !important;
    height: 44px !important;
    border: none !important;
    transition: all 0.15s ease !important;
}
.stButton > button:hover {
    background: #1e293b !important;
    transform: translateY(-1px);
}
.stButton > button:active {
    transform: scale(0.98);
}

.signal-card {
    background: white;
    border-radius: 18px;
    padding: 18px 18px 16px;
    margin: 10px 0 14px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03);
    border: 1px solid #f1f5f9;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.signal-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.06);
}
.signal-card:active {
    transform: translateY(0);
}

.buy    { border-left: 5px solid #10b981; }
.sell   { border-left: 5px solid #ef4444; }
.neutral{ border-left: 5px solid #94a3b8; }

.signal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
}
.signal-title {
    font-size: 1.15rem;
    font-weight: 700;
    letter-spacing: -0.01em;
}
.badge {
    font-size: 11px;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: 999px;
    letter-spacing: 0.02em;
}
.badge-buy    { background: #d1fae5; color: #065f46; }
.badge-sell   { background: #fee2e2; color: #991b1b; }
.badge-neutral{ background: #f1f5f9; color: #475569; }

.meta-row {
    color: #64748b;
    font-size: 13px;
    margin: 2px 0 10px;
}
.levels {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin: 10px 0 8px;
}
.level-box {
    background: #f8fafc;
    border-radius: 10px;
    padding: 8px 10px;
    text-align: center;
}
.level-label { font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: 0.04em; }
.level-value { font-size: 14px; font-weight: 700; margin-top: 2px; }

.outcome {
    display: inline-block;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 999px;
    background: #f1f5f9;
    color: #334155;
}

.stTabs [data-baseweb="tab-list"] { gap: 6px; background: transparent; }
.stTabs [data-baseweb="tab"] {
    border-radius: 12px !important;
    padding: 8px 14px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    transition: all 0.15s ease;
}
.stTabs [aria-selected="true"] {
    background: #0f172a !important;
    color: white !important;
}

.streamlit-expanderHeader {
    border-radius: 12px !important;
    font-weight: 600 !important;
}
.streamlit-expanderHeader:hover { background: #f8fafc !important; }

@media (max-width: 640px) {
    .signal-card { padding: 15px 15px 14px; border-radius: 16px; }
    .levels { grid-template-columns: 1fr 1fr 1fr; gap: 6px; }
    .level-value { font-size: 13px; }
    .signal-title { font-size: 1.05rem; }
}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='font-size:1.65rem; font-weight:800; margin-bottom:2px; letter-spacing:-0.02em;'>SUFX Signals</h1>", unsafe_allow_html=True)
st.caption("Multi-timeframe signals · Clean, fast, mobile-ready")

c1, c2 = st.columns([4, 1], gap="small")
with c1:
    symbol = st.text_input("Symbol", value="XAUUSD", label_visibility="collapsed", placeholder="XAUUSD, EURUSD, AAPL...")
with c2:
    if st.button("↻", use_container_width=True, help="Refresh"):
        st.rerun()

tfs = ["5m", "15m", "1h", "4h"]
tabs = st.tabs(tfs)

for tf, tab in zip(tfs, tabs):
    with tab:
        with st.spinner("Loading..."):
            df = fetch_data(symbol, tf, bars=150)

        if df.empty:
            st.info(f"No data for **{symbol}** on {tf}. Try XAUUSD, EURUSD, GC=F or AAPL.")
            continue

        sig = get_signal(df, tf)
        outcome = check_outcome(df, sig)

        side = sig["signal"]
        css = "buy" if side == "Buy" else "sell" if side == "Sell" else "neutral"
        badge_cls = "badge-buy" if side == "Buy" else "badge-sell" if side == "Sell" else "badge-neutral"
        icon = "▲" if side == "Buy" else "▼" if side == "Sell" else "●"

        st.markdown(f"""
        <div class="signal-card {css}">
            <div class="signal-header">
                <div class="signal-title">{icon} {side} · {tf}</div>
                <span class="badge {badge_cls}">{side.upper()}</span>
            </div>
            <div class="meta-row">
                Quality {sig.get('quality', 0)} · Score {sig.get('score', 0)} · {sig.get('regime', '—')}
            </div>
            <div class="levels">
                <div class="level-box">
                    <div class="level-label">Entry</div>
                    <div class="level-value">{sig.get('entry', '—')}</div>
                </div>
                <div class="level-box">
                    <div class="level-label">SL</div>
                    <div class="level-value">{sig.get('sl', '—')}</div>
                </div>
                <div class="level-box">
                    <div class="level-label">TP</div>
                    <div class="level-value">{sig.get('tp', '—')}</div>
                </div>
            </div>
            <div class="outcome">{outcome}</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Why this signal", expanded=False):
            reasons = sig.get("reasons", [])
            if reasons:
                for r in reasons:
                    st.write("• " + r)
            else:
                st.write("No detailed reasons available.")

        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df["open"], high=df["high"],
            low=df["low"], close=df["close"],
            increasing_line_color="#10b981",
            decreasing_line_color="#ef4444",
            name=""
        )])

        if "ema20" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df["ema20"], line=dict(color="#f59e0b", width=1.4), name="EMA20"))
            fig.add_trace(go.Scatter(x=df.index, y=df["ema50"], line=dict(color="#3b82f6", width=1.4), name="EMA50"))

        if side != "Neutral" and sig.get("sl") and sig.get("tp"):
            fig.add_hline(y=sig["entry"], line_dash="dot", line_color="#64748b", annotation_text="Entry")
            fig.add_hline(y=sig["sl"], line_color="#ef4444", line_width=1, annotation_text="SL")
            fig.add_hline(y=sig["tp"], line_color="#10b981", line_width=1, annotation_text="TP")

        fig.update_layout(
            height=340,
            margin=dict(l=4, r=4, t=16, b=4),
            xaxis_rangeslider_visible=False,
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", size=11),
            showlegend=False,
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False})

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
st.caption("Data from free sources · May be delayed · For research only — not financial advice.")
        
