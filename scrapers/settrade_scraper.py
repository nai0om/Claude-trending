"""Settrade Scraper — Playwright-based scraper for settrade.com stock data."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SettradeScraper:
    """Scrapes stock data from settrade.com using Playwright."""

    BASE_URL = "https://www.settrade.com"

    def __init__(self):
        self.browser = None
        self.page = None

    async def _init_browser(self):
        """Initialize Playwright browser."""
        from playwright.async_api import async_playwright

        pw = await async_playwright().start()
        self.browser = await pw.chromium.launch(headless=True)
        self.page = await self.browser.new_page()

    async def _close_browser(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()

    def fetch(self, symbol: str | None = None) -> list[dict]:
        """Fetch stock data from settrade (sync wrapper).

        Args:
            symbol: Specific stock symbol, or None for market overview.

        Returns:
            List of dicts with stock data.
        """
        import asyncio
        return asyncio.run(self._fetch_async(symbol))

    async def _fetch_async(self, symbol: str | None = None) -> list[dict]:
        """Fetch stock data asynchronously."""
        await self._init_browser()
        try:
            if symbol:
                return await self._fetch_stock(symbol)
            else:
                return await self._fetch_market_overview()
        finally:
            await self._close_browser()

    async def _fetch_stock(self, symbol: str) -> list[dict]:
        """Fetch individual stock data."""
        url = f"{self.BASE_URL}/equities/quote/{symbol}/overview"
        logger.info("Fetching %s from settrade...", url)
        await self.page.goto(url, wait_until="networkidle")

        # TODO: Extract price, volume, bid/ask from page
        # This is a stub — real selectors depend on settrade's DOM structure
        return [{
            "symbol": symbol,
            "source": "settrade",
            "fetched_at": datetime.now().isoformat(),
            "data": {},  # placeholder
        }]

    async def _fetch_market_overview(self) -> list[dict]:
        """Fetch SET market overview."""
        url = f"{self.BASE_URL}/equities/market-summary"
        logger.info("Fetching market overview from settrade...")
        await self.page.goto(url, wait_until="networkidle")

        # TODO: Extract SET index, top gainers/losers
        return [{
            "source": "settrade",
            "type": "market_overview",
            "fetched_at": datetime.now().isoformat(),
            "data": {},  # placeholder
        }]


def main():
    parser = argparse.ArgumentParser(description="Scrape data from settrade.com")
    parser.add_argument("--symbol", help="Stock symbol (omit for market overview)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    scraper = SettradeScraper()
    result = scraper.fetch(args.symbol)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
