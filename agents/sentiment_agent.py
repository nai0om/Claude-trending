"""Sentiment Analysis Agent — aggregates social media sentiment via Search Center API."""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.search_center_client import get_sentiment, get_channel_stats, search_posts

logger = logging.getLogger(__name__)


def analyze_sentiment(symbol: str, days: int = 7) -> dict:
    """Aggregate sentiment from Search Center API (Twitter, Facebook, webboard, news).

    Args:
        symbol: SET ticker symbol (e.g., 'PTT')
        days: Number of days to look back

    Returns:
        Dict with sentiment scores and source breakdown.
    """
    logger.info("Analyzing sentiment for %s (last %d days)...", symbol, days)

    # Get sentiment breakdown
    try:
        sentiment_data = get_sentiment(symbol, days=days)
    except Exception as e:
        logger.error("Failed to get sentiment: %s", e)
        return {
            "symbol": symbol,
            "sentiment_score": 0.0,
            "confidence": "Low",
            "sources": {},
            "note": f"Search Center API error: {e}",
        }

    if not sentiment_data.get("success"):
        return {
            "symbol": symbol,
            "sentiment_score": 0.0,
            "confidence": "Low",
            "sources": {},
            "note": "No sentiment data returned",
        }

    # Parse sentiment counts
    sentiment_map = {}
    for item in sentiment_data.get("data", []):
        sentiment_map[item["sentiment"]] = item["count"]

    positive = sentiment_map.get("positive", 0)
    neutral = sentiment_map.get("neutral", 0)
    negative = sentiment_map.get("negative", 0)
    total = positive + neutral + negative

    if total == 0:
        return {
            "symbol": symbol,
            "sentiment_score": 0.0,
            "confidence": "Low",
            "sources": {},
            "note": "No mentions found",
        }

    # Compute sentiment score: -1.0 to +1.0
    # Weighted: positive=+1, neutral=0, negative=-1
    score = (positive - negative) / total if total > 0 else 0.0

    # Confidence based on sample size
    if total >= 1000:
        confidence = "High"
    elif total >= 100:
        confidence = "Medium"
    else:
        confidence = "Low"

    # Label
    if score > 0.2:
        label = "Bullish"
    elif score < -0.2:
        label = "Bearish"
    else:
        label = "Neutral"

    # Get channel breakdown
    try:
        channel_data = get_channel_stats(symbol, days=days)
        sources = {}
        for ch in channel_data.get("data", []):
            sources[ch["channel"]] = {
                "count": ch["count"],
                "engagement": ch["engagement"],
            }
    except Exception:
        sources = {}

    # Get top posts for context
    try:
        top_posts = search_posts(symbol, days=days, sort_by="engagement", limit=5)
        top_mentions = []
        for post in top_posts.get("data", [])[:5]:
            top_mentions.append({
                "channel": post.get("channel", ""),
                "content": post.get("content", "")[:200],
                "engagement": post.get("engagement", {}),
                "sentiment": post.get("sentiment", ""),
                "date": post.get("date", ""),
                "url": post.get("url", ""),
            })
    except Exception:
        top_mentions = []

    return {
        "symbol": symbol,
        "analyzed_at": datetime.now().isoformat(),
        "period_days": days,
        "total_mentions": total,
        "sentiment_score": round(score, 4),
        "label": label,
        "confidence": confidence,
        "breakdown": {
            "positive": positive,
            "neutral": neutral,
            "negative": negative,
        },
        "sources": sources,
        "top_mentions": top_mentions,
    }


def main():
    parser = argparse.ArgumentParser(description="Sentiment analysis for SET stocks")
    parser.add_argument("--symbol", required=True, help="Stock symbol (e.g., PTT)")
    parser.add_argument("--days", type=int, default=7, help="Days to look back (default: 7)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    result = analyze_sentiment(args.symbol, days=args.days)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
