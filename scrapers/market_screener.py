"""Market Screener — Batch screen all SET stocks for technical signals.

Downloads price data via yfinance in chunks, computes RSI/MACD/volume indicators
using pure pandas/numpy, and categorizes stocks by signal type.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

# Add project root for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.set_stock_list import fetch_stock_list

logger = logging.getLogger(__name__)

OUTPUT_DIR = PROJECT_ROOT / "data" / "scans"
SETTINGS_FILE = PROJECT_ROOT / "config" / "settings.yaml"
THRESHOLDS_FILE = PROJECT_ROOT / "config" / "thresholds.yaml"

# Defaults (overridden by settings.yaml if present)
DEFAULT_CHUNK_SIZE = 50
DEFAULT_PERIOD = "3mo"
DEFAULT_TOP_N = 10

# Early signal defaults (overridden by thresholds.yaml if present)
DEFAULT_EARLY_SIGNALS = {
    "accumulation": {"rsi_low": 40, "rsi_high": 60, "volume_min": 1.5, "volume_max": 3.0},
    "macd_fresh_cross": {"lookback_bars": 2},
    "bb_squeeze": {"bb_length": 20, "bb_std": 2.0, "squeeze_lookback": 20},
    "volume_buildup": {"consecutive_days": 3, "range_lookback": 20, "max_range_position": 0.5},
}


def _load_settings() -> dict:
    """Load screener settings from config/settings.yaml."""
    try:
        import yaml
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            return cfg.get("screener", {})
    except ImportError:
        pass
    return {}


def _load_early_signal_config() -> dict:
    """Load early signal thresholds from config/thresholds.yaml."""
    try:
        import yaml
        if THRESHOLDS_FILE.exists():
            with open(THRESHOLDS_FILE, encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            return cfg.get("early_signals", DEFAULT_EARLY_SIGNALS)
    except ImportError:
        pass
    return DEFAULT_EARLY_SIGNALS


def _compute_macd_series(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.Series | None:
    """Compute full MACD histogram Series (needed to check previous bars)."""
    if len(close) < slow + signal:
        return None
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line - signal_line


def _compute_bb_width(close: pd.Series, length: int = 20, std: float = 2.0) -> pd.Series | None:
    """Compute Bollinger Band width Series: (upper - lower) / middle."""
    if len(close) < length:
        return None
    middle = close.rolling(window=length).mean()
    std_dev = close.rolling(window=length).std()
    upper = middle + std * std_dev
    lower = middle - std * std_dev
    width = (upper - lower) / middle.replace(0, np.nan)
    return width


def _detect_accumulation(
    rsi: float | None, vol_ratio: float | None, cfg: dict
) -> dict | None:
    """Detect accumulation: moderate volume + neutral RSI = smart money entering quietly."""
    if rsi is None or vol_ratio is None:
        return None
    if cfg["rsi_low"] <= rsi <= cfg["rsi_high"] and cfg["volume_min"] <= vol_ratio <= cfg["volume_max"]:
        # Strength: higher volume within range = stronger signal
        strength = round((vol_ratio - cfg["volume_min"]) / (cfg["volume_max"] - cfg["volume_min"]), 2)
        return {
            "signal": "ACCUMULATION",
            "detail": f"Vol {vol_ratio:.1f}x + RSI {rsi:.0f} (neutral zone)",
            "strength": strength,
        }
    return None


def _detect_macd_fresh_cross(hist_series: pd.Series | None, cfg: dict) -> dict | None:
    """Detect fresh MACD bullish crossover: histogram just turned positive within N bars."""
    if hist_series is None:
        return None
    lookback = cfg["lookback_bars"]
    # Need at least lookback+1 bars to check previous state
    if len(hist_series) < lookback + 2:
        return None
    recent = hist_series.iloc[-(lookback + 2):]
    # Current histogram must be positive
    if recent.iloc[-1] <= 0:
        return None
    # At least one bar in the lookback window before current must have been negative
    prev_bars = recent.iloc[-(lookback + 2):-1]
    if not (prev_bars < 0).any():
        return None
    # Strength: how big is the current positive histogram relative to the negative it came from
    min_neg = prev_bars.min()
    current = recent.iloc[-1]
    strength = min(round(float(current / abs(min_neg)) if min_neg != 0 else 0.5, 2), 1.0)
    return {
        "signal": "MACD_FRESH_CROSS",
        "detail": f"Histogram crossed +{current:.4f} (was {min_neg:.4f})",
        "strength": strength,
    }


def _detect_bb_squeeze(
    bb_width: pd.Series | None, cfg: dict
) -> dict | None:
    """Detect BB squeeze: BB width at its narrowest in N days = price about to explode."""
    if bb_width is None:
        return None
    lookback = cfg["squeeze_lookback"]
    if len(bb_width.dropna()) < lookback:
        return None
    recent = bb_width.dropna().iloc[-lookback:]
    current_width = recent.iloc[-1]
    if pd.isna(current_width):
        return None
    min_width = recent.min()
    # Current width must be within 5% of the minimum (essentially at or near the squeeze)
    if current_width <= min_width * 1.05:
        # Strength: how tight relative to the max width in the window
        max_width = recent.max()
        if max_width == 0 or pd.isna(max_width):
            return None
        squeeze_ratio = 1 - float(current_width / max_width)
        strength = round(min(squeeze_ratio, 1.0), 2)
        return {
            "signal": "BB_SQUEEZE",
            "detail": f"BB width {current_width:.4f} (min in {lookback}d, range {min_width:.4f}-{max_width:.4f})",
            "strength": strength,
        }
    return None


def _detect_volume_buildup(
    volume: pd.Series, close: pd.Series, cfg: dict
) -> dict | None:
    """Detect volume buildup: rising volume for N+ consecutive days + price in lower half of range."""
    consec = cfg["consecutive_days"]
    range_lookback = cfg["range_lookback"]
    max_pos = cfg["max_range_position"]

    if len(volume) < consec + 1 or len(close) < range_lookback:
        return None

    # Check consecutive volume increases
    recent_vol = volume.iloc[-(consec + 1):]
    increasing = all(
        recent_vol.iloc[i] < recent_vol.iloc[i + 1]
        for i in range(len(recent_vol) - 1)
    )
    if not increasing:
        return None

    # Check price is in lower half of range
    price_range = close.iloc[-range_lookback:]
    range_high = price_range.max()
    range_low = price_range.min()
    if range_high == range_low:
        return None
    current_pos = float((close.iloc[-1] - range_low) / (range_high - range_low))
    if current_pos > max_pos:
        return None

    # Strength: more days of buildup = stronger; lower price position = stronger
    vol_growth = float(recent_vol.iloc[-1] / recent_vol.iloc[0]) if recent_vol.iloc[0] > 0 else 1.0
    strength = round(min((1 - current_pos) * min(vol_growth / 3.0, 1.0), 1.0), 2)
    return {
        "signal": "VOLUME_BUILDUP",
        "detail": f"Vol rising {consec}d ({vol_growth:.1f}x), price at {current_pos:.0%} of range",
        "strength": strength,
    }


def _compute_rsi(close: pd.Series, period: int = 14) -> float | None:
    """Compute RSI using pure pandas. Returns latest RSI value."""
    if len(close) < period + 1:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return round(float(val), 2) if pd.notna(val) else None


def _compute_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict | None:
    """Compute MACD using pure pandas. Returns latest MACD values."""
    if len(close) < slow + signal:
        return None
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        "macd": round(float(macd_line.iloc[-1]), 4),
        "signal": round(float(signal_line.iloc[-1]), 4),
        "histogram": round(float(histogram.iloc[-1]), 4),
    }


def _compute_volume_ratio(volume: pd.Series, window: int = 20) -> float | None:
    """Compute volume ratio vs N-day average."""
    if len(volume) < window + 1:
        return None
    avg_vol = volume.iloc[-(window + 1):-1].mean()
    if avg_vol == 0 or pd.isna(avg_vol):
        return None
    latest_vol = volume.iloc[-1]
    return round(float(latest_vol / avg_vol), 2)


def _price_change(close: pd.Series, days: int) -> float | None:
    """Compute price change % over N days."""
    if len(close) < days + 1:
        return None
    old = close.iloc[-(days + 1)]
    new = close.iloc[-1]
    if old == 0 or pd.isna(old):
        return None
    return round(float((new - old) / old * 100), 2)


def screen_chunk(tickers: list[str], period: str = "1mo", early_cfg: dict | None = None) -> list[dict]:
    """Download and screen a chunk of tickers.

    Args:
        tickers: List of yfinance ticker strings (e.g., ["PTT.BK", "ADVANC.BK"])
        period: yfinance period string
        early_cfg: Early signal threshold config (loaded from thresholds.yaml)

    Returns:
        List of screening results per stock.
    """
    if early_cfg is None:
        early_cfg = DEFAULT_EARLY_SIGNALS
    results = []

    try:
        data = yf.download(
            tickers,
            period=period,
            group_by="ticker",
            progress=False,
            threads=True,
        )
    except Exception as e:
        logger.error("yfinance download failed for chunk: %s", e)
        return results

    if data.empty:
        return results

    for ticker in tickers:
        symbol = ticker.replace(".BK", "")
        try:
            # Extract per-ticker data
            if len(tickers) == 1:
                df = data
            else:
                if ticker not in data.columns.get_level_values(0):
                    continue
                df = data[ticker]

            if df.empty or len(df) < 5:
                continue

            close = df["Close"].dropna()
            volume = df["Volume"].dropna()

            if len(close) < 5:
                continue

            latest_close = float(close.iloc[-1])
            rsi = _compute_rsi(close)
            macd = _compute_macd(close)
            vol_ratio = _compute_volume_ratio(volume)
            chg_1d = _price_change(close, 1)
            chg_5d = _price_change(close, 5)

            # Determine signal
            signals = []
            if rsi is not None and rsi < 30:
                signals.append("OVERSOLD")
            if rsi is not None and rsi > 70:
                signals.append("OVERBOUGHT")
            if vol_ratio is not None and vol_ratio > 3.0:
                signals.append("VOLUME_SPIKE")
            if macd and macd["histogram"] > 0:
                signals.append("MACD_BULLISH")
            if macd and macd["histogram"] < 0:
                signals.append("MACD_BEARISH")

            # --- Early signal detection ---
            early_signals = []
            early_signal_details = []

            # 1. Accumulation
            acc = _detect_accumulation(rsi, vol_ratio, early_cfg["accumulation"])
            if acc:
                early_signals.append(acc["signal"])
                early_signal_details.append(acc)

            # 2. MACD Fresh Cross
            hist_series = _compute_macd_series(close)
            macd_cross = _detect_macd_fresh_cross(hist_series, early_cfg["macd_fresh_cross"])
            if macd_cross:
                early_signals.append(macd_cross["signal"])
                early_signal_details.append(macd_cross)

            # 3. BB Squeeze
            bb_cfg = early_cfg["bb_squeeze"]
            bb_width = _compute_bb_width(close, length=bb_cfg["bb_length"], std=bb_cfg["bb_std"])
            bb_sq = _detect_bb_squeeze(bb_width, bb_cfg)
            if bb_sq:
                early_signals.append(bb_sq["signal"])
                early_signal_details.append(bb_sq)

            # 4. Volume Buildup
            vol_bu = _detect_volume_buildup(volume, close, early_cfg["volume_buildup"])
            if vol_bu:
                early_signals.append(vol_bu["signal"])
                early_signal_details.append(vol_bu)

            results.append({
                "symbol": symbol,
                "close": round(latest_close, 2),
                "change_1d_pct": chg_1d,
                "change_5d_pct": chg_5d,
                "rsi": rsi,
                "macd_histogram": macd["histogram"] if macd else None,
                "volume_ratio": vol_ratio,
                "signals": signals,
                "early_signals": early_signals,
                "early_signal_details": early_signal_details,
            })

        except Exception as e:
            logger.debug("Failed to process %s: %s", symbol, e)
            continue

    return results


def run_screener(top_n: int = 10) -> dict:
    """Run the full market screener across all SET stocks.

    Args:
        top_n: Number of stocks to show in each category.

    Returns:
        Screener results dict with categories.
    """
    settings = _load_settings()
    chunk_size = settings.get("chunk_size", DEFAULT_CHUNK_SIZE)
    period = settings.get("period", DEFAULT_PERIOD)
    early_cfg = _load_early_signal_config()

    # Load stock list
    stocks = fetch_stock_list()
    symbols = [s["symbol"] for s in stocks]
    stock_info = {s["symbol"]: s for s in stocks}
    logger.info("Screening %d SET stocks (chunk_size=%d, period=%s)", len(symbols), chunk_size, period)

    # Convert to yfinance tickers
    tickers = [f"{sym}.BK" for sym in symbols]

    # Process in chunks
    all_results = []
    total_chunks = (len(tickers) + chunk_size - 1) // chunk_size

    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        chunk_num = i // chunk_size + 1
        logger.info("Processing chunk %d/%d (%d tickers)...", chunk_num, total_chunks, len(chunk))

        results = screen_chunk(chunk, period=period, early_cfg=early_cfg)
        all_results.extend(results)

        # Brief pause between chunks to be respectful
        if chunk_num < total_chunks:
            time.sleep(1)

    logger.info("Screened %d stocks successfully out of %d", len(all_results), len(symbols))

    # Categorize results
    valid = [r for r in all_results if r["close"] is not None]

    # Sort for categories
    top_gainers = sorted(
        [r for r in valid if r["change_1d_pct"] is not None],
        key=lambda x: x["change_1d_pct"],
        reverse=True,
    )[:top_n]

    top_losers = sorted(
        [r for r in valid if r["change_1d_pct"] is not None],
        key=lambda x: x["change_1d_pct"],
    )[:top_n]

    volume_spikes = sorted(
        [r for r in valid if r["volume_ratio"] is not None and r["volume_ratio"] > 3.0],
        key=lambda x: x["volume_ratio"],
        reverse=True,
    )[:top_n]

    oversold = sorted(
        [r for r in valid if r["rsi"] is not None and r["rsi"] < 30],
        key=lambda x: x["rsi"],
    )[:top_n]

    overbought = sorted(
        [r for r in valid if r["rsi"] is not None and r["rsi"] > 70],
        key=lambda x: x["rsi"],
        reverse=True,
    )[:top_n]

    # Early signals: stocks with any early signal, sorted by count then max strength
    early_signal_stocks = sorted(
        [r for r in valid if r.get("early_signals")],
        key=lambda x: (
            len(x["early_signals"]),
            max((d["strength"] for d in x.get("early_signal_details", [])), default=0),
        ),
        reverse=True,
    )[:top_n]

    # Enrich with sector info
    def enrich(items):
        for item in items:
            info = stock_info.get(item["symbol"], {})
            item["sector"] = info.get("sector") or info.get("industry") or ""
            item["name"] = info.get("name", "")
        return items

    result = {
        "screened_at": datetime.now().isoformat(),
        "total_screened": len(all_results),
        "total_attempted": len(symbols),
        "period": period,
        "categories": {
            "top_gainers": enrich(top_gainers),
            "top_losers": enrich(top_losers),
            "volume_spikes": enrich(volume_spikes),
            "oversold": enrich(oversold),
            "overbought": enrich(overbought),
            "early_signals": enrich(early_signal_stocks),
        },
        "all_results": all_results,
    }

    # Save to file
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_file = OUTPUT_DIR / f"screener_{date_str}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved screener results to %s", output_file)

    return result


def print_summary(result: dict, top_n: int = 10):
    """Print a human-readable summary of screener results."""
    cats = result["categories"]

    print(f"\n{'='*80}")
    print(f"  SET Market Screener — {result['screened_at'][:10]}")
    print(f"  Screened: {result['total_screened']}/{result['total_attempted']} stocks")
    print(f"{'='*80}")

    def print_table(title, items, sort_col):
        if not items:
            print(f"\n## {title}: (none)")
            return
        print(f"\n## {title}")
        print(f"{'#':>3} {'Symbol':<8} {'Sector':<15} {'Price':>10} {'Chg%':>8} {'RSI':>6} {'VolR':>6} {'Signal'}")
        print(f"{'---':>3} {'--------':<8} {'---------------':<15} {'----------':>10} {'--------':>8} {'------':>6} {'------':>6} {'------'}")
        for i, item in enumerate(items, 1):
            signals = ", ".join(item.get("signals", []))
            print(
                f"{i:>3} {item['symbol']:<8} {item.get('sector', '')[:15]:<15} "
                f"{item['close']:>10.2f} {item.get('change_1d_pct', 0) or 0:>7.2f}% "
                f"{item.get('rsi') or 0:>6.1f} {item.get('volume_ratio') or 0:>5.1f}x {signals}"
            )

    print_table("Top Gainers (1D)", cats["top_gainers"], "change_1d_pct")
    print_table("Top Losers (1D)", cats["top_losers"], "change_1d_pct")
    print_table("Volume Spikes (>3x avg)", cats["volume_spikes"], "volume_ratio")
    print_table("Oversold (RSI < 30)", cats["oversold"], "rsi")
    print_table("Overbought (RSI > 70)", cats["overbought"], "rsi")

    # Early signals table
    early = cats.get("early_signals", [])
    if early:
        print(f"\n## Early Signals (Potential Setups)")
        print(f"{'#':>3} {'Symbol':<8} {'Sector':<15} {'Price':>10} {'RSI':>6} {'VolR':>6} {'Signals':<30} {'Strength'}")
        print(f"{'---':>3} {'--------':<8} {'---------------':<15} {'----------':>10} {'------':>6} {'------':>6} {'------------------------------':<30} {'--------'}")
        for i, item in enumerate(early, 1):
            sig_names = ", ".join(item.get("early_signals", []))
            max_str = max((d["strength"] for d in item.get("early_signal_details", [])), default=0)
            strength_bar = "#" * int(max_str * 5)
            print(
                f"{i:>3} {item['symbol']:<8} {item.get('sector', '')[:15]:<15} "
                f"{item['close']:>10.2f} {item.get('rsi') or 0:>6.1f} {item.get('volume_ratio') or 0:>5.1f}x "
                f"{sig_names:<30} {strength_bar} ({max_str:.0%})"
            )

    print(f"\n{'='*80}")


def main():
    parser = argparse.ArgumentParser(description="Screen all SET stocks for technical signals")
    parser.add_argument("--top", type=int, default=10, help="Number of stocks per category (default: 10)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    result = run_screener(top_n=args.top)
    print_summary(result, top_n=args.top)


if __name__ == "__main__":
    main()
