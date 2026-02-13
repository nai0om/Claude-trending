"""News Scraper — scrapes Thai financial news sites."""

import argparse
import json
import logging
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class NewsScraper:
    """Scrapes Thai financial news from multiple sources."""

    NEWS_SOURCES = [
        {"name": "Kaohoon", "url": "https://www.kaohoon.com", "search": "/search?q={}"},
        {"name": "Bangkokbiznews", "url": "https://www.bangkokbiznews.com", "search": "/search?q={}"},
        {"name": "ThaiPBS", "url": "https://www.thaipbs.or.th", "search": "/search?q={}"},
    ]

    def __init__(self):
        self.client = httpx.Client(
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36",
            },
            timeout=30.0,
            follow_redirects=True,
        )

    def fetch(self, symbol: str) -> list[dict]:
        """Fetch recent news articles for a stock.

        Args:
            symbol: Stock symbol (e.g., 'PTT')

        Returns:
            List of article dicts with title, source, date, summary.
        """
        logger.info("Fetching news for %s...", symbol)
        all_articles = []

        for source in self.NEWS_SOURCES:
            try:
                articles = self._fetch_source(source, symbol)
                all_articles.extend(articles)
            except Exception as e:
                logger.warning("Failed to fetch from %s: %s", source["name"], e)

        logger.info("Found %d total articles for %s", len(all_articles), symbol)
        return all_articles

    def _fetch_source(self, source: dict, symbol: str) -> list[dict]:
        """Fetch articles from a single news source."""
        search_url = source["url"] + source["search"].format(symbol)
        response = self.client.get(search_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        articles = []

        # TODO: Source-specific selectors
        for item in soup.select("article, .news-item, .search-result")[:10]:
            title_el = item.select_one("h2, h3, .title, a")
            if not title_el:
                continue

            articles.append({
                "title": title_el.get_text(strip=True),
                "source": source["name"],
                "url": title_el.get("href", ""),
                "date": datetime.now().strftime("%Y-%m-%d"),  # TODO: parse actual date
                "summary": "",  # TODO: extract summary
                "fetched_at": datetime.now().isoformat(),
            })

        return articles

    def close(self):
        """Close HTTP client."""
        self.client.close()


def main():
    parser = argparse.ArgumentParser(description="Scrape Thai financial news")
    parser.add_argument("--symbol", required=True, help="Stock symbol")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    scraper = NewsScraper()
    try:
        result = scraper.fetch(args.symbol)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
