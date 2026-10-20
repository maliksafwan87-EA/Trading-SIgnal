"""
Signal engine for multi-asset, multi-timeframe Buy/Sell/Neutral signals.
Logic kept modular and unchanged unless explicitly requested.

Data sources:
- Forex & Metals (XAUUSD, EURUSD, etc.): biquote.io (free real-time mid prices + OHLC with tickVolume). Truly live from MT5-style feed. Volume is tick volume (not exchange volume).
- Stocks: yfinance (Yahoo Finance). Near real-time during market hours for many symbols, otherwise delayed ~15 min. Real exchange volume where available.
Fallback: if biquote fails, try yfinance mapping.

Signals based on classic TA research (EMA trend, RSI momentum, MACD, volume confirmation, ATR for levels).
"""

import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

# Common symbol mappings
FOREX_METALS = {
    "XAUUSD", "GOLD", "XAU", "XAUS",
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD",
    "EURGBP", "EURJPY", "GBPJPY", "XAGUSD", "SILVER",
    "BTCUSD", "ETHUSD"  # also supported
}

def normalize_symbol(user_input: str) -> tuple[str, str]:
    """Return (provider_symbol, asset_class) where asset_class is 'forex_metal' or 'stock'."""
    s = user_input.upper().strip().replace("/", "").replace("-", "")
    if s in FOREX_METALS or s.endswith("USD") and len(s) <= 7:
        return s, "forex_metal"
    # yfinance style for stocks/futures
    if s in ("GC=F", "SI=F", "CL=F", "ES=F"):
        return s, "stock"  # treat futures via yfinance
    return s, "stock"


def fetch_ohlc(symbol: str, interval: str, limit: int = 200) -> pd.DataFrame:
    """Fetch OHLCV. Prefer biquote for forex/metals (live), yfinance for stocks."""
    provider_sym, asset_class = normalize_symbol(symbol)
    
    if asset_class == "forex_metal":
        try:
            url = f"https://biquote.io/api/{provider_sym}/ohlc"
            params = {"interval": interval, "limit": limit}
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            if "bars" not in data or not data["bars"]:
                raise ValueError("No bars")
            df = pd.DataFrame(data["bars"])
            df["openTime"] = pd.to_datetime(df["openTime"])
            df = df.set_index("openTime").sort_index()
            # Rename and use tickVolume if volume is 0
            df = df.rename(columns={
                "open": "Open", "high": "High", "low": "Low", "close": "Close",
                "volume": "Volume", "tickVolume": "TickVolume"
            })
            if "Volume" not in df.columns or (df["Volume"] == 0).all():
                df["Volume"] = df.get("TickVolume", 0)
            df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
            if len(df) > 10:
                return df
        except Exception:
            pass  # fallback below
    
    # yfinance fallback or stocks
    yf_interval = {"5m": "5m", "15m": "15m", "1h": "1h", "4h": "1h", "1d": "1d", "1wk": "1wk"}.get(interval, "1h")
    period = "60d" if interval in ("5m", "15m", "1h", "4h") else "2y"
    try:
        ticker = yf.Ticker(provider_sym if asset_class == "stock" else provider_sym + "=X" if not provider_sym.endswith("=X") and not provider_sym.endswith("=F") else provider_sym)
        # Special cases
        if provider_sym in ("XAUUSD", "GOLD", "XAU"):
            ticker = yf.Ticker("GC=F")
        elif provider_sym in ("XAGUSD", "SILVER"):
            ticker = yf.Ticker("SI=F")
        df = ticker.history(period=period, interval=yf_interval, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        if interval == "4h" and yf_interval == "1h":
            df = df.resample("4h").agg({
                "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
            }).dropna()
        return df.tail(limit)
    except Exception:
        return pd.DataFrame()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or len(df) < 50:
        return df
    close = df["Close"]
    df["EMA20"] = close.ewm(span=20, adjust=False).mean()
    df["EMA50"] = close.ewm(span=50, adjust=False).mean()
    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
    # ATR
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - close.shift()).abs()
    low_close = (df["Low"] - close.shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(14).mean()
    # Volume SMA
    df["VolSMA"] = df["Volume"].rolling(20).mean()
    return df


def generate_signal(df: pd.DataFrame) -> dict:
    """Core signal logic. Do not change unless requested.
    
    Buy: price > EMA20 > EMA50, RSI 45-70, MACD hist > 0, volume > avg
    Sell: price < EMA20 < EMA50, RSI 30-55, MACD hist < 0, volume > avg
    Neutral: otherwise
    TP/SL based on ATR (risk 1.5 ATR, reward 2.5 ATR)
    """
    if df.empty or len(df) < 55:
        return {
            "signal": "Neutral",
            "reasons": ["Insufficient data"],
            "entry": None, "tp": None, "sl": None,
            "atr": None, "price": None, "confidence": 0
        }
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    price = float(last["Close"])
    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])
    rsi = float(last["RSI"]) if not pd.isna(last["RSI"]) else 50
    macd_hist = float(last["MACD_Hist"]) if not pd.isna(last["MACD_Hist"]) else 0
    vol = float(last["Volume"])
    vol_sma = float(last["VolSMA"]) if not pd.isna(last["VolSMA"]) else 0
    atr = float(last["ATR"]) if not pd.isna(last["ATR"]) else price * 0.01
    
    reasons = []
    score = 0
    
    # Trend
    if price > ema20 > ema50:
        reasons.append("Uptrend: Price > EMA20 > EMA50")
        score += 2
    elif price < ema20 < ema50:
        reasons.append("Downtrend: Price < EMA20 < EMA50")
        score -= 2
    else:
        reasons.append("Mixed/flat trend vs EMAs")
    
    # Momentum RSI
    if 45 <= rsi <= 70:
        reasons.append(f"RSI {rsi:.1f} in bullish zone")
        score += 1
    elif 30 <= rsi <= 55:
        reasons.append(f"RSI {rsi:.1f} in bearish zone")
        score -= 1
    elif rsi > 70:
        reasons.append(f"RSI {rsi:.1f} overbought")
        score -= 0.5
    elif rsi < 30:
        reasons.append(f"RSI {rsi:.1f} oversold")
        score += 0.5
    else:
        reasons.append(f"RSI {rsi:.1f} neutral")
    
    # MACD
    if macd_hist > 0:
        reasons.append("MACD histogram positive (bullish momentum)")
        score += 1
    elif macd_hist < 0:
        reasons.append("MACD histogram negative (bearish momentum)")
        score -= 1
    
    # Volume confirmation
    if vol > vol_sma * 1.1 and vol_sma > 0:
        reasons.append("Volume above average (confirmation)")
        score += 0.5
    elif vol_sma > 0:
        reasons.append("Volume at or below average")
    
    # Decide signal
    if score >= 3:
        signal = "Buy"
        entry = price
        tp = round(entry + 2.5 * atr, 5)
        sl = round(entry - 1.5 * atr, 5)
        confidence = min(90, int(50 + score * 10))
    elif score <= -3:
        signal = "Sell"
        entry = price
        tp = round(entry - 2.5 * atr, 5)
        sl = round(entry + 1.5 * atr, 5)
        confidence = min(90, int(50 + abs(score) * 10))
    else:
        signal = "Neutral"
        entry = price
        tp = None
        sl = None
        confidence = 40
    
    return {
        "signal": signal,
        "reasons": reasons,
        "entry": round(entry, 5) if entry else None,
        "tp": tp,
        "sl": sl,
        "atr": round(atr, 5),
        "price": round(price, 5),
        "confidence": confidence,
        "timestamp": df.index[-1]
    }


def check_outcome(df: pd.DataFrame, signal_info: dict, lookback_bars: int = 50) -> str:
    """After a signal is generated, check if subsequent bars hit TP or SL.
    Returns 'TP Hit', 'SL Hit', or 'Active' (or 'N/A').
    Uses high/low of bars after the signal bar.
    """
    if signal_info["signal"] == "Neutral" or signal_info["tp"] is None:
        return "N/A"
    
    sig_time = signal_info.get("timestamp")
    if sig_time is None or sig_time not in df.index:
        # Approximate: check last N bars
        post = df.tail(lookback_bars)
    else:
        post = df.loc[sig_time:]
    
    if len(post) <= 1:
        return "Active"
    
    direction = signal_info["signal"]
    tp = signal_info["tp"]
    sl = signal_info["sl"]
    
    for _, bar in post.iloc[1:].iterrows():
        if direction == "Buy":
            if bar["High"] >= tp:
                return "TP Hit"
            if bar["Low"] <= sl:
                return "SL Hit"
        else:  # Sell
            if bar["Low"] <= tp:
                return "TP Hit"
            if bar["High"] >= sl:
                return "SL Hit"
    return "Active"


def compute_poc(df: pd.DataFrame, bins: int = 30) -> float | None:
    """Simple Point of Control: price level with highest volume (binned).
    Useful for POI/POC marking on delayed or tick volume data.
    """
    if df.empty or df["Volume"].sum() == 0:
        return None
    try:
        price_min, price_max = df["Low"].min(), df["High"].max()
        if price_max <= price_min:
            return None
        bins_edges = np.linspace(price_min, price_max, bins + 1)
        vol_by_bin = np.zeros(bins)
        for _, row in df.iterrows():
            # Approximate volume distribution across the bar range
            idx = np.digitize(row["Close"], bins_edges) - 1
            idx = np.clip(idx, 0, bins - 1)
            vol_by_bin[idx] += row["Volume"]
        poc_idx = vol_by_bin.argmax()
        poc_price = (bins_edges[poc_idx] + bins_edges[poc_idx + 1]) / 2
        return round(float(poc_price), 5)
    except Exception:
        return None
