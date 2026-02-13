"""News Analysis Agent — analyzes Thai and international news impact on stocks."""

import argparse
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def analyze_news(symbol: str) -> dict:
    """Fetch and analyze news for a SET stock.

    Args:
        symbol: SET ticker symbol (e.g., 'PTT')

    Returns:
        Dict with news items and impact assessment.
    """
    from scrapers.news_scraper import NewsScraper

    scraper = NewsScraper()
    articles = scraper.fetch(symbol)

    if not articles:
        return {
            "symbol": symbol,
            "news_count": 0,
            "impact_score": 0.0,
            "articles": [],
            "note": "No recent news found",
        }

    # Score each article's potential impact
    scored_articles = []
    for article in articles:
        scored_articles.append({
            "title": article["title"],
            "source": article["source"],
            "date": article["date"],
            "url": article.get("url", ""),
            "summary": article.get("summary", ""),
        })

    return {
        "symbol": symbol,
        "analyzed_at": datetime.now().isoformat(),
        "news_count": len(scored_articles),
        "articles": scored_articles,
    }


def main():
    parser = argparse.ArgumentParser(description="News analysis for SET stocks")
    parser.add_argument("--symbol", required=True, help="Stock symbol (e.g., PTT)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    result = analyze_news(args.symbol)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
