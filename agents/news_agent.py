"""News Analysis Agent — fetches and analyzes news via Search Center API."""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.search_center_client import search_news, search_posts

logger = logging.getLogger(__name__)


def analyze_news(symbol: str, days: int = 7) -> dict:
    """Fetch and analyze news for a SET stock via Search Center API.

    Args:
        symbol: SET ticker symbol (e.g., 'PTT')
        days: Number of days to look back

    Returns:
        Dict with news articles and impact assessment.
    """
    logger.info("Fetching news for %s (last %d days)...", symbol, days)

    try:
        news_data = search_news(symbol, days=days, limit=20)
    except Exception as e:
        logger.error("Failed to fetch news: %s", e)
        return {
            "symbol": symbol,
            "news_count": 0,
            "articles": [],
            "note": f"Search Center API error: {e}",
        }

    if not news_data.get("success"):
        return {
            "symbol": symbol,
            "news_count": 0,
            "articles": [],
            "note": "No news data returned",
        }

    articles = []
    for post in news_data.get("data", []):
        articles.append({
            "title": post.get("content", "")[:200],
            "source": post.get("domain", ""),
            "channel": post.get("channel", "news"),
            "date": post.get("date", ""),
            "url": post.get("url", ""),
            "sentiment": post.get("sentiment", "neutral"),
            "engagement": post.get("engagement", {}),
        })

    # Also fetch webboard discussions (Pantip etc.)
    try:
        webboard_data = search_posts(
            symbol, days=days, channels=["webboard"], sort_by="engagement", limit=10,
        )
        for post in webboard_data.get("data", []):
            articles.append({
                "title": post.get("content", "")[:200],
                "source": post.get("domain", ""),
                "channel": "webboard",
                "date": post.get("date", ""),
                "url": post.get("url", ""),
                "sentiment": post.get("sentiment", "neutral"),
                "engagement": post.get("engagement", {}),
            })
    except Exception:
        pass

    # Count sentiment in news
    pos = sum(1 for a in articles if a["sentiment"] == "positive")
    neg = sum(1 for a in articles if a["sentiment"] == "negative")
    neu = sum(1 for a in articles if a["sentiment"] == "neutral")

    return {
        "symbol": symbol,
        "analyzed_at": datetime.now().isoformat(),
        "period_days": days,
        "news_count": len(articles),
        "news_sentiment": {
            "positive": pos,
            "neutral": neu,
            "negative": neg,
        },
        "articles": articles,
    }


def main():
    parser = argparse.ArgumentParser(description="News analysis for SET stocks")
    parser.add_argument("--symbol", required=True, help="Stock symbol (e.g., PTT)")
    parser.add_argument("--days", type=int, default=7, help="Days to look back (default: 7)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    result = analyze_news(args.symbol, days=args.days)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
