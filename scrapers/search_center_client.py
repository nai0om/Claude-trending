"""Search Center API Client — unified social media + news search via local Elasticsearch API."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:4344"

# Thai name / keyword mappings for SET stocks
STOCK_KEYWORDS = {
    "PTT": "PTT OR ปตท",
    "ADVANC": "ADVANC OR AIS OR แอดวานซ์",
    "AOT": "AOT OR ท่าอากาศยาน OR การบินไทย",
    "CPALL": "CPALL OR ซีพี ออลล์ OR เซเว่น",
    "GULF": "GULF OR กัลฟ์",
    "KBANK": "KBANK OR กสิกรไทย OR กสิกร",
    "SCB": "SCB OR ไทยพาณิชย์",
    "SCC": "SCC OR ปูนซิเมนต์ไทย OR เอสซีจี",
    "BDMS": "BDMS OR กรุงเทพดุสิตเวชการ OR บำรุงราษฎร์",
    "DELTA": "DELTA OR เดลต้า",
}

ALL_CHANNELS = ["twitter", "facebook", "news", "webboard", "tiktok", "youtube", "instagram"]
SOCIAL_CHANNELS = ["twitter", "facebook", "webboard"]
NEWS_CHANNELS = ["news"]


def _get_keyword(symbol: str) -> str:
    """Get search keyword string for a stock symbol."""
    return STOCK_KEYWORDS.get(symbol.upper(), symbol)


def _post(endpoint: str, payload: dict) -> dict:
    """POST to Search Center API."""
    url = f"{BASE_URL}{endpoint}"
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


def health_check() -> dict:
    """Check API health."""
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(f"{BASE_URL}/health")
        return resp.json()


def search_posts(
    symbol: str,
    days: int = 7,
    channels: list[str] | None = None,
    sentiment: str | None = None,
    sort_by: str = "engagement",
    limit: int = 20,
) -> dict:
    """Search social media posts for a stock.

    Args:
        symbol: SET ticker symbol (e.g., 'PTT')
        days: Number of days to look back
        channels: List of channels to search (default: all social)
        sentiment: Filter by 'positive', 'neutral', or 'negative'
        sort_by: Sort by 'engagement', 'date', or 'virality'
        limit: Max results to return

    Returns:
        API response with posts data.
    """
    now = datetime.utcnow()
    payload = {
        "keyword": _get_keyword(symbol),
        "startDate": (now - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z"),
        "endDate": now.strftime("%Y-%m-%dT23:59:59Z"),
        "channels": channels or SOCIAL_CHANNELS,
        "sortBy": sort_by,
        "order": "desc",
        "limit": limit,
    }
    if sentiment:
        payload["sentiment"] = sentiment

    return _post("/api/v1/search", payload)


def get_sentiment(symbol: str, days: int = 7, channels: list[str] | None = None) -> dict:
    """Get sentiment breakdown for a stock.

    Args:
        symbol: SET ticker symbol
        days: Number of days to look back
        channels: Channels to include

    Returns:
        Sentiment stats with positive/neutral/negative counts.
    """
    now = datetime.utcnow()
    return _post("/api/v1/stats/sentiment", {
        "keyword": _get_keyword(symbol),
        "startDate": (now - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z"),
        "endDate": now.strftime("%Y-%m-%dT23:59:59Z"),
        "channels": channels or ALL_CHANNELS,
    })


def get_channel_stats(symbol: str, days: int = 7) -> dict:
    """Get mention count per channel for a stock."""
    now = datetime.utcnow()
    return _post("/api/v1/stats/channels", {
        "keyword": _get_keyword(symbol),
        "startDate": (now - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z"),
        "endDate": now.strftime("%Y-%m-%dT23:59:59Z"),
    })


def compare_stocks(symbols: list[str], days: int = 7) -> dict:
    """Compare sentiment and engagement across multiple stocks.

    Args:
        symbols: List of SET ticker symbols
        days: Number of days to look back

    Returns:
        Comparison data with counts, engagement, sentiment per stock.
    """
    now = datetime.utcnow()
    return _post("/api/v1/stats/compare", {
        "startDate": (now - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z"),
        "endDate": now.strftime("%Y-%m-%dT23:59:59Z"),
        "keywords": [
            {"name": sym, "keyword": _get_keyword(sym)} for sym in symbols
        ],
    })


def get_timeline(symbol: str, days: int = 7, interval: str = "day") -> dict:
    """Get mention/engagement timeline for a stock.

    Args:
        symbol: SET ticker symbol
        days: Number of days to look back
        interval: 'hour', 'day', 'week', or 'month'

    Returns:
        Timeline data with daily counts and engagement.
    """
    now = datetime.utcnow()
    return _post("/api/v1/stats/timeline", {
        "startDate": (now - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z"),
        "endDate": now.strftime("%Y-%m-%dT23:59:59Z"),
        "keywords": [{"name": symbol, "keyword": _get_keyword(symbol)}],
        "interval": interval,
    })


def search_news(symbol: str, days: int = 7, limit: int = 20) -> dict:
    """Search news articles for a stock.

    Args:
        symbol: SET ticker symbol
        days: Number of days to look back
        limit: Max results

    Returns:
        API response with news posts.
    """
    return search_posts(symbol, days=days, channels=NEWS_CHANNELS, sort_by="date", limit=limit)


def get_top_hashtags(symbol: str, days: int = 7, limit: int = 10) -> dict:
    """Get top hashtags associated with a stock."""
    now = datetime.utcnow()
    return _post("/api/v1/stats/hashtags", {
        "keyword": _get_keyword(symbol),
        "startDate": (now - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z"),
        "endDate": now.strftime("%Y-%m-%dT23:59:59Z"),
        "channels": ["twitter", "facebook"],
        "limit": limit,
    })


def main():
    parser = argparse.ArgumentParser(description="Search Center API Client for SET stocks")
    parser.add_argument("--symbol", help="Stock symbol (e.g., PTT)")
    parser.add_argument("--action", default="sentiment",
                        choices=["sentiment", "search", "compare", "timeline", "news", "channels", "hashtags", "health"],
                        help="Action to perform")
    parser.add_argument("--days", type=int, default=7, help="Days to look back (default: 7)")
    parser.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")
    parser.add_argument("--symbols", nargs="+", help="Multiple symbols for compare")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    if args.action == "health":
        result = health_check()
    elif args.action == "sentiment":
        result = get_sentiment(args.symbol, days=args.days)
    elif args.action == "search":
        result = search_posts(args.symbol, days=args.days, limit=args.limit)
    elif args.action == "compare":
        symbols = args.symbols or [args.symbol]
        result = compare_stocks(symbols, days=args.days)
    elif args.action == "timeline":
        result = get_timeline(args.symbol, days=args.days)
    elif args.action == "news":
        result = search_news(args.symbol, days=args.days, limit=args.limit)
    elif args.action == "channels":
        result = get_channel_stats(args.symbol, days=args.days)
    elif args.action == "hashtags":
        result = get_top_hashtags(args.symbol, days=args.days)
    else:
        result = {"error": "Unknown action"}

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
