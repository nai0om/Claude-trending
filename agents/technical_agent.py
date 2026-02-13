"""Technical Analysis Agent — computes RSI, MACD, Bollinger Bands via pandas-ta."""

import argparse
import json
import logging
from datetime import datetime

import pandas as pd
import pandas_ta as ta
import yfinance as yf

logger = logging.getLogger(__name__)

TICKER_SUFFIX = ".BK"


def compute_indicators(symbol: str, period: str = "6mo") -> dict:
    """Compute technical indicators for a stock.

    Args:
        symbol: SET ticker symbol (e.g., 'PTT')
        period: yfinance period string

    Returns:
        Dict with RSI, MACD, Bollinger Bands, support/resistance levels.
    """
    ticker = yf.Ticker(f"{symbol}{TICKER_SUFFIX}")
    df = ticker.history(period=period)

    if df.empty:
        return {"symbol": symbol, "error": "No data available"}

    # RSI (14-period)
    df["RSI"] = ta.rsi(df["Close"], length=14)

    # MACD (12, 26, 9)
    macd = ta.macd(df["Close"], fast=12, slow=26, signal=9)
    df = pd.concat([df, macd], axis=1)

    # Bollinger Bands (20, 2)
    bbands = ta.bbands(df["Close"], length=20, std=2)
    df = pd.concat([df, bbands], axis=1)

    latest = df.iloc[-1]
    close = float(latest["Close"])

    # Support/Resistance from recent highs/lows
    recent = df.tail(20)
    support = float(recent["Low"].min())
    resistance = float(recent["High"].max())

    return {
        "symbol": symbol,
        "computed_at": datetime.now().isoformat(),
        "close": close,
        "indicators": {
            "rsi": round(float(latest["RSI"]), 2) if pd.notna(latest["RSI"]) else None,
            "macd": round(float(latest.get("MACD_12_26_9", 0)), 4),
            "macd_signal": round(float(latest.get("MACDs_12_26_9", 0)), 4),
            "macd_histogram": round(float(latest.get("MACDh_12_26_9", 0)), 4),
            "bb_upper": round(float(latest.get("BBU_20_2.0", 0)), 2),
            "bb_middle": round(float(latest.get("BBM_20_2.0", 0)), 2),
            "bb_lower": round(float(latest.get("BBL_20_2.0", 0)), 2),
        },
        "levels": {
            "support": round(support, 2),
            "resistance": round(resistance, 2),
        },
        "signals": generate_signals(latest, close, support, resistance),
    }


def generate_signals(latest: pd.Series, close: float, support: float, resistance: float) -> list[str]:
    """Generate human-readable technical signals."""
    signals = []
    rsi = latest.get("RSI")

    if pd.notna(rsi):
        if rsi < 30:
            signals.append("RSI oversold (<30)")
        elif rsi > 70:
            signals.append("RSI overbought (>70)")

    macd_hist = latest.get("MACDh_12_26_9", 0)
    if pd.notna(macd_hist):
        if macd_hist > 0:
            signals.append("MACD bullish")
        else:
            signals.append("MACD bearish")

    bb_lower = latest.get("BBL_20_2.0")
    bb_upper = latest.get("BBU_20_2.0")
    if pd.notna(bb_lower) and close <= bb_lower:
        signals.append("Price at lower Bollinger Band")
    elif pd.notna(bb_upper) and close >= bb_upper:
        signals.append("Price at upper Bollinger Band")

    return signals


def main():
    parser = argparse.ArgumentParser(description="Technical analysis for SET stocks")
    parser.add_argument("--symbol", required=True, help="Stock symbol (e.g., PTT)")
    parser.add_argument("--period", default="6mo", help="Data period (default: 6mo)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    result = compute_indicators(args.symbol, period=args.period)
    print(json.dumps(result, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
