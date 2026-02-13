"""Sentiment Analysis Agent — aggregates Pantip + Twitter Thai stock sentiment."""

import argparse
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def analyze_sentiment(symbol: str) -> dict:
    """Aggregate sentiment from multiple Thai social sources.

    Args:
        symbol: SET ticker symbol (e.g., 'PTT')

    Returns:
        Dict with sentiment scores and source breakdown.
    """
    # TODO: Import and run scrapers, then analyze with WangchanBERTa
    from scrapers.pantip_scraper import PantipScraper
    from scrapers.twitter_scraper import TwitterScraper
    from analysis.thai_sentiment import analyze_texts

    pantip = PantipScraper()
    twitter = TwitterScraper()

    pantip_posts = pantip.fetch(symbol)
    tweets = twitter.fetch(symbol)

    all_texts = [p["text"] for p in pantip_posts] + [t["text"] for t in tweets]

    if not all_texts:
        return {
            "symbol": symbol,
            "sentiment_score": 0.0,
            "confidence": "Low",
            "sources": {"pantip": 0, "twitter": 0},
            "note": "No social data found",
        }

    sentiment = analyze_texts(all_texts)

    return {
        "symbol": symbol,
        "analyzed_at": datetime.now().isoformat(),
        "sentiment_score": sentiment["score"],
        "label": sentiment["label"],
        "confidence": sentiment["confidence"],
        "sources": {
            "pantip": len(pantip_posts),
            "twitter": len(tweets),
        },
        "top_mentions": sentiment.get("top_keywords", []),
    }


def main():
    parser = argparse.ArgumentParser(description="Sentiment analysis for SET stocks")
    parser.add_argument("--symbol", required=True, help="Stock symbol (e.g., PTT)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    result = analyze_sentiment(args.symbol)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
