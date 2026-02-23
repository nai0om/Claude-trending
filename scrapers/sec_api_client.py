"""SEC API Client — REST client for SEC Open Data (api.sec.or.th).

Migrated from the old api-portal.sec.or.th to the new SEC Open Data portal
(secopendata.sec.or.th) which uses api.sec.or.th as the API base URL.

API Products used:
  - One Report: company info, financial statements, ratios
  - Endpoints: /v1/one-report/sbo/{year}/info/{lang}
                /v1/one-report/fs/{year}/financial_statement/{unique_id}
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


class SECApiClient:
    """Client for Thailand SEC Open Data API — fetches company financial data."""

    BASE_URL = "https://api.sec.or.th"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("SEC_API_KEY", "")
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Accept": "application/json",
            },
            timeout=30.0,
        )
        self._company_cache: dict[str, dict] = {}

    def _resolve_unique_id(self, symbol: str, report_year: str) -> str | None:
        """Look up a company's unique_id from its SET ticker symbol.

        The One Report API requires unique_id (e.g., 'C0000001074' for PTT)
        rather than the ticker symbol. This method fetches the company list
        for the given report_year and caches it.
        """
        cache_key = report_year
        if cache_key not in self._company_cache:
            try:
                response = self.client.get(
                    f"/v1/one-report/sbo/{report_year}/info/E",
                )
                if response.status_code == 204:
                    logger.warning("No company data for year %s", report_year)
                    return None
                response.raise_for_status()
                companies = response.json()
                self._company_cache[cache_key] = {
                    c["symbol"]: c for c in companies if "symbol" in c
                }
            except httpx.HTTPError as e:
                logger.error("Failed to fetch company list for year %s: %s", report_year, e)
                return None

        company = self._company_cache.get(cache_key, {}).get(symbol.upper())
        return company["unique_id"] if company else None

    def fetch(self, symbol: str, periods: int = 8) -> list[dict]:
        """Fetch financial statements for a company from One Report.

        The new SEC Open Data API provides annual financial statements
        from One Report filings. Each report_year contains:
          - Balance Sheet (financial_statement=01)
          - Income Statement (financial_statement=02)
          - Cash Flow (financial_statement=03)
          - Financial Ratios (financial_statement=04)

        Each item includes values for 3 years: asof_year, asof_yesteryear,
        asof_year_before_yesteryear.

        Args:
            symbol: SET ticker symbol (e.g., 'PTT')
            periods: Number of report years to try (searches backwards)

        Returns:
            List of financial statement items from the most recent available year.
        """
        logger.info("Fetching financial data for %s from SEC Open Data API...", symbol)

        current_year = datetime.now().year
        for year_offset in range(periods):
            report_year = str(current_year - 1 - year_offset)
            unique_id = self._resolve_unique_id(symbol, report_year)
            if not unique_id:
                continue

            try:
                response = self.client.get(
                    f"/v1/one-report/fs/{report_year}/financial_statement/{unique_id}",
                )
                if response.status_code == 204:
                    logger.debug("No financial data for %s year %s", symbol, report_year)
                    continue
                response.raise_for_status()
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    logger.info("Found %d financial items for %s (year %s)", len(data), symbol, report_year)
                    return data
            except httpx.HTTPError as e:
                logger.error("SEC API request failed for %s year %s: %s", symbol, report_year, e)
                continue

        logger.warning("No financial data found for %s in any recent year", symbol)
        return []

    def fetch_company_info(self, symbol: str) -> dict:
        """Fetch company profile information from One Report.

        Searches backwards from the most recent year to find company info.
        """
        current_year = datetime.now().year
        for year_offset in range(4):
            report_year = str(current_year - 1 - year_offset)
            try:
                response = self.client.get(
                    f"/v1/one-report/sbo/{report_year}/info/E",
                )
                if response.status_code == 204:
                    continue
                response.raise_for_status()
                companies = response.json()
                for company in companies:
                    if company.get("symbol", "").upper() == symbol.upper():
                        return company
            except httpx.HTTPError as e:
                logger.error("Failed to fetch company info for year %s: %s", report_year, e)
                continue

        logger.warning("No company info found for %s", symbol)
        return {}

    def fetch_financial_ratios(self, symbol: str) -> list[dict]:
        """Fetch financial ratios (subset of financial statements where financial_statement=04)."""
        all_items = self.fetch(symbol)
        return [item for item in all_items if item.get("financial_statement") == "04"]

    def close(self):
        """Close HTTP client."""
        self.client.close()


def main():
    parser = argparse.ArgumentParser(description="Fetch financial data from SEC Open Data API")
    parser.add_argument("--symbol", required=True, help="Stock symbol (e.g., PTT)")
    parser.add_argument("--periods", type=int, default=8, help="Number of years to search back (default: 8)")
    parser.add_argument("--info", action="store_true", help="Fetch company info instead of financials")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    client = SECApiClient()
    try:
        if args.info:
            result = client.fetch_company_info(args.symbol)
        else:
            result = client.fetch(args.symbol, periods=args.periods)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    main()
