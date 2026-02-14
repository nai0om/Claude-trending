"""Pantip Scraper — scrapes ห้องสินธร (Sinthorn room) for stock sentiment."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class PantipScraper:
    """Scrapes stock-related posts from Pantip's Sinthorn forum."""

    BASE_URL = "https://pantip.com"
    FORUM_URL = "https://pantip.com/forum/sinthorn"

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

    def fetch(self, symbol: str | None = None) -> list[dict]:
        """Fetch recent posts mentioning a stock symbol.

        Args:
            symbol: Stock symbol to search for (e.g., 'PTT')

        Returns:
            List of post dicts with title, text, date, comments count.
        """
        logger.info("Fetching Pantip posts for %s...", symbol or "all")

        try:
            if symbol:
                url = f"{self.BASE_URL}/search?q={symbol}&tag=sinthorn"
            else:
                url = self.FORUM_URL

            response = self.client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            posts = self._parse_posts(soup, symbol)
            logger.info("Found %d posts", len(posts))
            return posts

        except httpx.HTTPError as e:
            logger.error("Pantip scraping failed: %s", e)
            return []

    def _parse_posts(self, soup: BeautifulSoup, symbol: str | None) -> list[dict]:
        """Parse post elements from Pantip HTML."""
        posts = []

        # TODO: Update selectors based on actual Pantip DOM structure
        for item in soup.select(".post-item, .topic-item")[:20]:
            title_el = item.select_one(".post-title, .topic-title, a")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)

            # Filter by symbol if specified
            if symbol and symbol.upper() not in title.upper():
                text_el = item.select_one(".post-excerpt, .post-desc")
                text = text_el.get_text(strip=True) if text_el else ""
                if symbol.upper() not in text.upper():
                    continue
            else:
                text_el = item.select_one(".post-excerpt, .post-desc")
                text = text_el.get_text(strip=True) if text_el else ""

            posts.append({
                "title": title,
                "text": text,
                "url": title_el.get("href", ""),
                "source": "pantip",
                "fetched_at": datetime.now().isoformat(),
            })

        return posts

    def close(self):
        """Close HTTP client."""
        self.client.close()


def main():
    parser = argparse.ArgumentParser(description="Scrape Pantip Sinthorn forum")
    parser.add_argument("--symbol", help="Stock symbol to search for")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    scraper = PantipScraper()
    try:
        result = scraper.fetch(args.symbol)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
