"""Volume analysis — volume profile, money flow, unusual volume detection."""

import pandas as pd


def compute_volume_ratio(volumes: pd.Series, lookback: int = 20) -> float:
    """Compute current volume relative to average.

    Args:
        volumes: Volume series
        lookback: Period for average calculation

    Returns:
        Ratio of latest volume to average (e.g., 2.0 = 2x average).
    """
    if len(volumes) < lookback + 1:
        return 1.0

    avg_volume = volumes.iloc[-(lookback + 1):-1].mean()
    current_volume = volumes.iloc[-1]

    if avg_volume == 0:
        return 0.0

    return round(float(current_volume / avg_volume), 2)


def detect_unusual_volume(volumes: pd.Series, threshold: float = 1.5, lookback: int = 20) -> dict:
    """Detect unusual volume activity.

    Args:
        volumes: Volume series
        threshold: Minimum ratio to flag as unusual
        lookback: Period for baseline

    Returns:
        Dict with is_unusual flag, ratio, and signal.
    """
    ratio = compute_volume_ratio(volumes, lookback)
    is_unusual = ratio >= threshold

    if ratio >= 3.0:
        signal = "Very high volume (3x+)"
    elif ratio >= 2.0:
        signal = "High volume (2x+)"
    elif ratio >= threshold:
        signal = "Above average volume"
    else:
        signal = "Normal volume"

    return {
        "volume_ratio": ratio,
        "is_unusual": is_unusual,
        "signal": signal,
        "current_volume": int(volumes.iloc[-1]) if len(volumes) > 0 else 0,
        "avg_volume": int(volumes.iloc[-(lookback + 1):-1].mean()) if len(volumes) > lookback else 0,
    }


def compute_money_flow(df: pd.DataFrame, length: int = 14) -> dict:
    """Compute Money Flow Index (MFI) and on-balance volume.

    Args:
        df: DataFrame with High, Low, Close, Volume columns
        length: MFI period

    Returns:
        Dict with MFI value and interpretation.
    """
    if len(df) < length + 1:
        return {"mfi": None, "signal": "Insufficient data"}

    # Typical price
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    raw_mf = tp * df["Volume"]

    # Positive/negative money flow
    pos_mf = pd.Series(0.0, index=df.index)
    neg_mf = pd.Series(0.0, index=df.index)

    for i in range(1, len(df)):
        if tp.iloc[i] > tp.iloc[i - 1]:
            pos_mf.iloc[i] = raw_mf.iloc[i]
        else:
            neg_mf.iloc[i] = raw_mf.iloc[i]

    pos_sum = pos_mf.rolling(length).sum()
    neg_sum = neg_mf.rolling(length).sum()

    mfr = pos_sum / neg_sum.replace(0, 1)
    mfi = 100 - (100 / (1 + mfr))

    latest_mfi = float(mfi.iloc[-1])

    if latest_mfi > 80:
        signal = "Overbought (MFI > 80)"
    elif latest_mfi < 20:
        signal = "Oversold (MFI < 20)"
    else:
        signal = "Neutral"

    return {
        "mfi": round(latest_mfi, 2),
        "signal": signal,
    }


def generate_volume_score(volume_data: dict) -> float:
    """Generate volume score from -100 to +100.

    High volume with price increase = positive.
    High volume with price decrease = negative.
    """
    ratio = volume_data.get("volume_ratio", 1.0)
    price_direction = volume_data.get("price_change_pct", 0)

    # Volume above average amplifies the price signal
    if ratio > 1.5:
        amplifier = min(ratio, 4.0) / 2  # cap at 2x amplification
    else:
        amplifier = 0.5

    score = price_direction * amplifier * 10
    return max(-100, min(100, score))
