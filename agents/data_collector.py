"""Data Collector Agent — fetches price/volume data from SET via yfinance."""

import argparse
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import yfinance as yf

logger = logging.getLogger(__name__)

TICKER_SUFFIX = ".BK"


def load_watchlist() -> list[dict]:
    """Load stock symbols from watchlist.json."""
    watchlist_path = Path(__file__).parent.parent / "data" / "watchlist.json"
    with open(watchlist_path) as f:
        data = json.load(f)
    return data["watchlist"]


def fetch_price_data(symbol: str, period: str = "6mo") -> dict:
    """Fetch price and volume data for a SET stock.

    Args:
        symbol: SET ticker symbol (e.g., 'PTT')
        period: yfinance period string (e.g., '1mo', '6mo', '1y')

    Returns:
        Dict with OHLCV data and metadata.
    """
    ticker = yf.Ticker(f"{symbol}{TICKER_SUFFIX}")
    hist = ticker.history(period=period)

    if hist.empty:
        logger.warning("No data returned for %s", symbol)
        return {"symbol": symbol, "error": "No data available", "data": None}

    latest = hist.iloc[-1]
    return {
        "symbol": symbol,
        "fetched_at": datetime.now().isoformat(),
        "period": period,
        "latest": {
            "date": str(hist.index[-1].date()),
            "open": float(latest["Open"]),
            "high": float(latest["High"]),
            "low": float(latest["Low"]),
            "close": float(latest["Close"]),
            "volume": int(latest["Volume"]),
        },
        "history_rows": len(hist),
        "data": hist.to_dict(orient="index"),
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch SET stock price/volume data")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--symbol", type=str, help="Stock symbol (e.g., PTT)")
    group.add_argument("--all", action="store_true", help="Fetch all watchlist stocks")
    parser.add_argument("--period", default="6mo", help="Data period (default: 6mo)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    if args.all:
        watchlist = load_watchlist()
        results = []
        for stock in watchlist:
            logger.info("Fetching data for %s...", stock["symbol"])
            result = fetch_price_data(stock["symbol"], period=args.period)
            results.append(result)
        print(json.dumps({"results": results, "count": len(results)}, default=str))
    else:
        result = fetch_price_data(args.symbol, period=args.period)
        print(json.dumps(result, default=str))


if __name__ == "__main__":
    main()
