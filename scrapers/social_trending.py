"""Social Trending — Discover trending SET stocks from social media via Search Center API.

Searches broad Thai stock-related keywords, extracts stock symbols from posts,
validates against the SET stock list, and gets sentiment/engagement data.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import httpx

# Add project root for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scrapers.set_stock_list import fetch_stock_list

logger = logging.getLogger(__name__)

OUTPUT_DIR = PROJECT_ROOT / "data" / "scans"
WATCHLIST_FILE = PROJECT_ROOT / "data" / "watchlist.json"

# Search Center API base (from config/settings.yaml)
SEARCH_CENTER_URL = "http://localhost:4344"

# Broad Thai stock market keywords to discover trending symbols
DISCOVERY_KEYWORDS = [
    "หุ้น",       # stocks
    "SET",        # SET exchange
    "ปันผล",      # dividends
    "กำไร",       # profits
    "ขาดทุน",     # losses
    "งบการเงิน",   # financial statements
    "พอร์ตหุ้น",   # stock portfolio
    "หุ้นปั่น",    # manipulated stock
    "หุ้นเด้ง",    # bouncing stock
    "แนวรับ แนวต้าน",  # support/resistance
]

# Common English words that look like stock tickers but aren't
FALSE_POSITIVE_SYMBOLS = {
    "THE", "AND", "FOR", "NOT", "ALL", "ARE", "BUT", "HAS", "HAD", "HER",
    "HIS", "HOW", "ITS", "LET", "MAY", "NEW", "NOW", "OLD", "OUR", "OUT",
    "OWN", "SAY", "SHE", "TOO", "USE", "WAY", "WHO", "BOY", "DID", "GET",
    "HIM", "SET", "TOP", "TWO", "WHY", "ADD", "AGE", "AGO", "AID", "AIM",
    "AIR", "ASK", "ATE", "BAD", "BAG", "BAN", "BAR", "BED", "BIG", "BIT",
    "BOX", "BUS", "BUY", "CAN", "CAR", "CUT", "DAD", "DAY", "DOG", "DRY",
    "EAR", "EAT", "END", "EYE", "FAR", "FAT", "FEW", "FLY", "FUN", "GAS",
    "GOD", "GOT", "GUN", "GUY", "HIT", "HOT", "ICE", "ILL", "JOB", "KEY",
    "KID", "LAW", "LAY", "LED", "LEG", "LIE", "LOT", "LOW", "MAP", "MEN",
    "MET", "MIX", "MOM", "NET", "NOR", "ODD", "OFF", "OIL", "ONE", "PAY",
    "PER", "PIN", "PIT", "PRO", "PUT", "RAN", "RAW", "RED", "RID", "RUN",
    "SAD", "SAT", "SAW", "SEA", "SIT", "SIX", "SKI", "SON", "TAX", "TEN",
    "THE", "TIE", "TIP", "TON", "VAN", "WAR", "WAS", "WET", "WON", "YES",
    "YET", "YOU", "CEO", "CFO", "CTO", "IPO", "ETF", "GDP", "QOQ", "YOY",
    "USD", "THB", "EUR", "JPY", "COVID", "LINE", "POST", "NEWS", "LIKE",
    "LOVE", "GOOD", "BEST", "FREE", "HOME", "LAST", "LONG", "MADE", "MORE",
    "MOST", "MUCH", "MUST", "NAME", "NEXT", "ONLY", "OPEN", "OVER", "PLAY",
    "REAL", "SAME", "SELL", "SHOW", "SIDE", "SIZE", "SOME", "SURE", "TAKE",
    "TELL", "THAN", "THAT", "THEM", "THEN", "THEY", "THIS", "TIME", "TRUE",
    "TURN", "TYPE", "UNIT", "UPON", "VERY", "WANT", "WEEK", "WELL", "WENT",
    "WERE", "WHAT", "WHEN", "WILL", "WITH", "WORD", "WORK", "YEAR", "YOUR",
    "NULL", "VOID", "CALL", "BEAR", "BULL", "HOLD", "STOP", "LOSS", "GAIN",
    "RISK", "RATE", "FUND", "CASH", "DEBT", "LOAN", "BANK", "MOVE", "VOTE",
    "DEAL", "PLAN", "LIVE", "LOOK", "EACH", "BACK", "COME", "FIND",
    "GIVE", "HAND", "HIGH", "JUST", "KEEP", "KNOW",
}

# Regex to extract potential stock ticker symbols from text
SYMBOL_PATTERN = re.compile(r"\b([A-Z][A-Z0-9]{1,7})\b")


def _load_watchlist_symbols() -> set[str]:
    """Load watchlist symbols to identify non-watchlist discoveries."""
    try:
        data = json.loads(WATCHLIST_FILE.read_text(encoding="utf-8"))
        return {s["symbol"] for s in data.get("watchlist", [])}
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def _post_search_center(endpoint: str, payload: dict) -> dict:
    """POST to Search Center API."""
    url = f"{SEARCH_CENTER_URL}{endpoint}"
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


def _search_keyword(keyword: str, days: int = 3) -> list[dict]:
    """Search a single keyword via Search Center API."""
    now = datetime.utcnow()
    payload = {
        "keyword": keyword,
        "startDate": (now - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z"),
        "endDate": now.strftime("%Y-%m-%dT23:59:59Z"),
        "channels": ["twitter", "facebook", "webboard", "news"],
        "sortBy": "engagement",
        "order": "desc",
        "limit": 100,
    }
    try:
        return _post_search_center("/api/v1/search", payload).get("data", [])
    except (httpx.HTTPError, json.JSONDecodeError) as e:
        logger.warning("Search failed for keyword '%s': %s", keyword, e)
        return []


def extract_symbols_from_posts(posts: list[dict], valid_symbols: set[str]) -> Counter:
    """Extract and count stock symbols mentioned in posts.

    Args:
        posts: List of post dicts with 'title' and/or 'content' fields.
        valid_symbols: Set of known SET stock symbols for validation.

    Returns:
        Counter of symbol -> mention count.
    """
    counter = Counter()

    for post in posts:
        text = " ".join([
            post.get("title", ""),
            post.get("content", ""),
            post.get("text", ""),
        ])

        found = SYMBOL_PATTERN.findall(text)
        for sym in found:
            sym = sym.upper()
            if sym in FALSE_POSITIVE_SYMBOLS:
                continue
            if sym in valid_symbols:
                counter[sym] += 1

    return counter


def get_trending_sentiment(symbols: list[str], days: int = 3) -> dict:
    """Get sentiment and engagement data for discovered symbols.

    Args:
        symbols: List of stock symbols to compare.
        days: Days to look back.

    Returns:
        Comparison data from Search Center API.
    """
    if not symbols:
        return {}

    # Import keyword mapping from search_center_client
    try:
        from scrapers.search_center_client import _get_keyword
    except ImportError:
        _get_keyword = lambda s: s  # noqa: E731

    now = datetime.utcnow()
    payload = {
        "startDate": (now - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z"),
        "endDate": now.strftime("%Y-%m-%dT23:59:59Z"),
        "keywords": [
            {"name": sym, "keyword": _get_keyword(sym)} for sym in symbols
        ],
    }

    try:
        return _post_search_center("/api/v1/stats/compare", payload)
    except (httpx.HTTPError, json.JSONDecodeError) as e:
        logger.warning("Compare API failed: %s", e)
        return {}


def discover_trending(days: int = 3, top_n: int = 20) -> dict:
    """Discover trending SET stocks from social media.

    Args:
        days: Number of days to search.
        top_n: Number of top trending symbols to return.

    Returns:
        Dict with trending stocks, sentiment data, and metadata.
    """
    # Load valid SET symbols
    all_stocks = fetch_stock_list()
    valid_symbols = {s["symbol"] for s in all_stocks}
    stock_info = {s["symbol"]: s for s in all_stocks}

    # Load watchlist for comparison
    watchlist_symbols = _load_watchlist_symbols()

    logger.info("Searching %d keywords across social media (last %d days)...", len(DISCOVERY_KEYWORDS), days)

    # Search all keywords and collect posts
    all_posts = []
    for keyword in DISCOVERY_KEYWORDS:
        posts = _search_keyword(keyword, days=days)
        all_posts.extend(posts)
        logger.info("  '%s': %d posts found", keyword, len(posts))

    logger.info("Total posts collected: %d", len(all_posts))

    # Extract and count symbol mentions
    symbol_counts = extract_symbols_from_posts(all_posts, valid_symbols)

    # Get top trending symbols
    top_symbols = symbol_counts.most_common(top_n)

    if not top_symbols:
        logger.info("No trending symbols discovered")
        result = {
            "discovered_at": datetime.now().isoformat(),
            "days_searched": days,
            "keywords_searched": len(DISCOVERY_KEYWORDS),
            "posts_analyzed": len(all_posts),
            "trending": [],
            "new_discoveries": [],
        }
        _save_result(result)
        return result

    logger.info("Top trending symbols: %s", ", ".join(f"{s}({c})" for s, c in top_symbols[:10]))

    # Get sentiment/engagement for top symbols
    trending_syms = [sym for sym, _ in top_symbols]
    sentiment_data = get_trending_sentiment(trending_syms[:20], days=days)

    # Build results
    sentiment_by_symbol = {}
    if isinstance(sentiment_data, dict):
        for item in sentiment_data.get("data", []):
            name = item.get("name", "")
            sentiment_by_symbol[name] = {
                "total_mentions": item.get("count", 0),
                "engagement": item.get("engagement", 0),
                "positive": item.get("positive", 0),
                "neutral": item.get("neutral", 0),
                "negative": item.get("negative", 0),
                "sentiment_score": item.get("sentimentScore", 0),
            }

    trending = []
    new_discoveries = []

    for symbol, mention_count in top_symbols:
        info = stock_info.get(symbol, {})
        sent = sentiment_by_symbol.get(symbol, {})

        entry = {
            "symbol": symbol,
            "name": info.get("name", ""),
            "sector": info.get("sector") or info.get("industry") or "",
            "mentions_in_posts": mention_count,
            "total_mentions": sent.get("total_mentions", mention_count),
            "engagement": sent.get("engagement", 0),
            "sentiment_score": sent.get("sentiment_score", 0),
            "positive": sent.get("positive", 0),
            "neutral": sent.get("neutral", 0),
            "negative": sent.get("negative", 0),
            "in_watchlist": symbol in watchlist_symbols,
        }

        # Determine signal
        score = entry["sentiment_score"]
        if score > 0.3:
            entry["signal"] = "BULLISH_TRENDING"
        elif score < -0.3:
            entry["signal"] = "BEARISH_TRENDING"
        else:
            entry["signal"] = "NEUTRAL_TRENDING"

        if mention_count >= 10:
            entry["signal"] += " HOT"

        trending.append(entry)

        if symbol not in watchlist_symbols:
            new_discoveries.append(entry)

    result = {
        "discovered_at": datetime.now().isoformat(),
        "days_searched": days,
        "keywords_searched": len(DISCOVERY_KEYWORDS),
        "posts_analyzed": len(all_posts),
        "trending": trending,
        "new_discoveries": new_discoveries,
    }

    _save_result(result)
    return result


def _save_result(result: dict):
    """Save trending results to file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_file = OUTPUT_DIR / f"trending_{date_str}.json"
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved trending results to %s", output_file)


def print_summary(result: dict):
    """Print a human-readable summary of trending results."""
    print(f"\n{'='*80}")
    print(f"  Social Trending Discovery — {result['discovered_at'][:10]}")
    print(f"  Searched {result['keywords_searched']} keywords, analyzed {result['posts_analyzed']} posts")
    print(f"{'='*80}")

    trending = result["trending"]
    if not trending:
        print("\n  No trending stocks discovered.")
        return

    # All trending
    print(f"\n## All Trending ({len(trending)} stocks)")
    print(f"{'#':>3} {'Symbol':<8} {'Sector':<15} {'Mentions':>9} {'Engage':>8} {'Sent':>6} {'WL':>3} {'Signal'}")
    print(f"{'---':>3} {'--------':<8} {'---------------':<15} {'---------':>9} {'--------':>8} {'------':>6} {'---':>3} {'------'}")
    for i, item in enumerate(trending, 1):
        wl = "Y" if item["in_watchlist"] else ""
        print(
            f"{i:>3} {item['symbol']:<8} {item.get('sector', '')[:15]:<15} "
            f"{item['mentions_in_posts']:>9} {item.get('engagement', 0):>8} "
            f"{item.get('sentiment_score', 0):>6.2f} {wl:>3} {item.get('signal', '')}"
        )

    # New discoveries (not in watchlist)
    discoveries = result["new_discoveries"]
    if discoveries:
        print(f"\n## New Discoveries (not in watchlist): {len(discoveries)}")
        for i, item in enumerate(discoveries[:10], 1):
            print(
                f"  {i}. {item['symbol']} ({item.get('sector', '')}) — "
                f"{item['mentions_in_posts']} mentions, "
                f"sentiment: {item.get('sentiment_score', 0):.2f}, "
                f"signal: {item.get('signal', '')}"
            )

    print(f"\n{'='*80}")


def main():
    parser = argparse.ArgumentParser(description="Discover trending SET stocks from social media")
    parser.add_argument("--days", type=int, default=3, help="Days to search (default: 3)")
    parser.add_argument("--top", type=int, default=20, help="Top N trending symbols (default: 20)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    result = discover_trending(days=args.days, top_n=args.top)
    print_summary(result)


if __name__ == "__main__":
    main()
