"""Technical indicator calculations — pure computation, no I/O."""

import pandas as pd
import pandas_ta as ta


def compute_rsi(close: pd.Series, length: int = 14) -> pd.Series:
    """Compute Relative Strength Index."""
    return ta.rsi(close, length=length)


def compute_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Compute MACD (line, signal, histogram)."""
    return ta.macd(close, fast=fast, slow=slow, signal=signal)


def compute_bollinger_bands(close: pd.Series, length: int = 20, std: float = 2.0) -> pd.DataFrame:
    """Compute Bollinger Bands (upper, middle, lower)."""
    return ta.bbands(close, length=length, std=std)


def compute_sma(close: pd.Series, length: int = 50) -> pd.Series:
    """Compute Simple Moving Average."""
    return ta.sma(close, length=length)


def compute_ema(close: pd.Series, length: int = 20) -> pd.Series:
    """Compute Exponential Moving Average."""
    return ta.ema(close, length=length)


def find_support_resistance(df: pd.DataFrame, lookback: int = 20) -> dict:
    """Find support and resistance levels from recent price action.

    Args:
        df: DataFrame with 'High' and 'Low' columns
        lookback: Number of periods to look back

    Returns:
        Dict with support and resistance levels.
    """
    recent = df.tail(lookback)
    return {
        "support": float(recent["Low"].min()),
        "resistance": float(recent["High"].max()),
        "support_date": str(recent["Low"].idxmin()),
        "resistance_date": str(recent["High"].idxmax()),
    }


def generate_technical_score(indicators: dict) -> float:
    """Generate a technical score from -100 to +100.

    Args:
        indicators: Dict with RSI, MACD histogram, BB position, etc.

    Returns:
        Score from -100 (strongly bearish) to +100 (strongly bullish).
    """
    score = 0.0

    # RSI contribution (-30 to +30)
    rsi = indicators.get("rsi")
    if rsi is not None:
        if rsi < 30:
            score += 30 * (30 - rsi) / 30
        elif rsi > 70:
            score -= 30 * (rsi - 70) / 30

    # MACD contribution (-25 to +25)
    macd_hist = indicators.get("macd_histogram")
    if macd_hist is not None:
        score += max(-25, min(25, macd_hist * 100))

    # Bollinger Band position contribution (-20 to +20)
    bb_position = indicators.get("bb_position")  # 0=lower, 0.5=middle, 1=upper
    if bb_position is not None:
        score -= (bb_position - 0.5) * 40

    # Trend (SMA) contribution (-25 to +25)
    price_vs_sma = indicators.get("price_vs_sma50")  # ratio
    if price_vs_sma is not None:
        deviation = (price_vs_sma - 1) * 100
        score += max(-25, min(25, deviation * 5))

    return max(-100, min(100, score))
