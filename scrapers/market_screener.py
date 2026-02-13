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

# Defaults (overridden by settings.yaml if present)
DEFAULT_CHUNK_SIZE = 50
DEFAULT_PERIOD = "3mo"
DEFAULT_TOP_N = 10


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


def screen_chunk(tickers: list[str], period: str = "1mo") -> list[dict]:
    """Download and screen a chunk of tickers.

    Args:
        tickers: List of yfinance ticker strings (e.g., ["PTT.BK", "ADVANC.BK"])
        period: yfinance period string

    Returns:
        List of screening results per stock.
    """
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

            results.append({
                "symbol": symbol,
                "close": round(latest_close, 2),
                "change_1d_pct": chg_1d,
                "change_5d_pct": chg_5d,
                "rsi": rsi,
                "macd_histogram": macd["histogram"] if macd else None,
                "volume_ratio": vol_ratio,
                "signals": signals,
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

        results = screen_chunk(chunk, period=period)
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
