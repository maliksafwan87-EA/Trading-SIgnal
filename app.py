import streamlit as st
import plotly.graph_objects as go
from engine import fetch_data, get_signal, check_outcome
import pandas as pd

st.set_page_config(
    page_title="SUFX Signals",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Modern, attractive, click-responsive styles
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    
    .stApp { 
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
        color: #0f172a;
    }
    
    /* Header */
    h1 { font-weight: 700; letter-spacing: -0.02em; color: #0f172a !important; }
    
    /* Input & button polish */
    .stTextInput > div > div > input {
        border-radius: 10px !important;
        border: 1px solid #e2e8f0 !important;
        padding: 0.6rem 0.9rem !important;
        transition: all 0.2s ease;
    }
    .stTextInput > div > div > input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
    }
    
    .stButton > button {
        border-radius: 10px !important;
        background: #0f172a !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        transition: all 0.15s ease !important;
        height: 42px;
    }
    .stButton > button:hover {
        background: #1e293b !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(15,23,42,0.15);
    }
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* Signal cards - attractive + click responsive */
    .signal-card {
        background: white;
        border-radius: 16px;
        padding: 18px 20px;
        margin: 12px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
        border: 1px solid #f1f5f9;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: pointer;
    }
    .signal-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 25px -5px rgba(0,0,0,0.08), 0 8px 10px -6px rgba(0,0,0,0.04);
        border-color: #e2e8f0;
    }
    .signal-card:active {
        transform: translateY(0);
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    
    .buy { border-left: 5px solid #10b981; }
    .sell { border-left: 5px solid #ef4444; }
    .neutral { border-left: 5px solid #94a3b8; }
    
    .signal-title {
        font-size: 1.25rem;
        font-weight: 700;
        margin: 0 0 6px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .meta { color: #64748b; font-size: 0.85rem; margin: 4px 0; }
    .levels { font-size: 0.9rem; margin: 6px 0; color: #334155; }
    .outcome { 
        font-size: 0.8rem; 
        font-weight: 600; 
        margin-top: 8px;
        padding: 4px 10px;
        border-radius: 999px;
        display: inline-block;
        background: #f1f5f9;
    }
    
    /* Expander polish */
    .streamlit-expanderHeader {
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: background 0.15s ease;
    }
    .streamlit-expanderHeader:hover {
        background: #f8fafc !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px !important;
        padding: 8px 16px !important;
        font-weight: 600 !important;
        transition: all 0.15s ease;
    }
    .stTabs [aria-selected="true"] {
        background: #0f172a !important;
        color: white !important;
    }
    
    /* Mobile tweaks */
    @media (max-width: 640px) {
        .signal-card { padding: 14px 16px; border-radius: 14px; }
        .signal-title { font-size: 1.1rem; }
    }
</style>
""", unsafe_allow_html=True)

st.title("📈 SUFX Signals")
st.caption("Clean multi-timeframe signals · Buy / Sell / Neutral with reasons")

# Top controls
col1, col2 = st.columns([3, 1], gap="small")
with col1:
    symbol = st.text_input("Asset Symbol", value="XAUUSD", placeholder="XAUUSD, EURUSD, AAPL...", label_visibility="collapsed")
with col2:
    refresh = st.button("Refresh", use_container_width=True)

if refresh:
    st.rerun()

timeframes = ["5m", "15m", "1h", "4h"]
tabs = st.tabs(timeframes)

for tf, tab in zip(timeframes, tabs):
    with tab:
        with st.spinner(f"Loading {tf}..."):
            df = fetch_data(symbol, tf, bars=150)
        
        if df.empty:
            st.warning(f"No data for **{symbol}** on {tf}. Try XAUUSD, EURUSD, AAPL, or GC=F.")
            continue
        
        sig = get_signal(df, tf)
        outcome = check_outcome(df, sig)
        
        css = "buy" if sig["signal"] == "Buy" else "sell" if sig["signal"] == "Sell" else "neutral"
        icon = "🟢" if sig["signal"] == "Buy" else "🔴" if sig["signal"] == "Sell" else "⚪"
        
        # Attractive clickable-feeling card
        st.markdown(f"""
        <div class="signal-card {css}">
            <div class="signal-title">{icon} {sig["signal"]} · {tf}</div>
            <div class="meta">Quality {sig["quality"]} · Score {sig.get("score", 0)} · {sig["regime"]}</div>
            <div class="levels">
                Entry <b>{sig["entry"]}</b> &nbsp;·&nbsp; 
                SL <b>{sig["sl"]}</b> &nbsp;·&nbsp; 
                TP <b>{sig["tp"]}</b>
            </div>
            <div class="outcome">{outcome}</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("Reasons", expanded=False):
            for r in sig["reasons"]:
                st.write("• " + r)
        
        # Chart
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df["open"], high=df["high"], low=df["low"], close=df["close"],
            name="Price",
            increasing_line_color="#10b981",
            decreasing_line_color="#ef4444"
        )])
        if "ema20" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df["ema20"], line=dict(color="#f59e0b", width=1.5), name="EMA20"))
            fig.add_trace(go.Scatter(x=df.index, y=df["ema50"], line=dict(color="#3b82f6", width=1.5), name="EMA50"))
        if sig["sl"] and sig["tp"] and sig["signal"] != "Neutral":
            fig.add_hline(y=sig["entry"], line_dash="dot", line_color="#64748b", annotation_text="Entry")
            fig.add_hline(y=sig["sl"], line_color="#ef4444", line_width=1, annotation_text="SL")
            fig.add_hline(y=sig["tp"], line_color="#10b981", line_width=1, annotation_text="TP")
        
        fig.update_layout(
            height=360,
            margin=dict(l=8, r=8, t=24, b=8),
            xaxis_rangeslider_visible=False,
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", size=12),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown("---")
st.caption("Free data sources · Delayed. For research only — not financial advice.")
