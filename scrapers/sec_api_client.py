"""SEC API Client — REST client for SEC API Portal (api-portal.sec.or.th)."""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


class SECApiClient:
    """Client for Thailand SEC API Portal — fetches company financial statements."""

    BASE_URL = "https://api-portal.sec.or.th/public"

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

    def fetch(self, symbol: str, periods: int = 8) -> list[dict]:
        """Fetch financial statements for a company.

        Args:
            symbol: SET ticker symbol (e.g., 'PTT')
            periods: Number of quarterly periods to fetch

        Returns:
            List of financial statement dicts (quarterly).
        """
        logger.info("Fetching %d periods of financial data for %s from SEC API...", periods, symbol)

        try:
            # Fetch company financial statements
            response = self.client.get(
                f"/v1/companies/{symbol}/financial-statements",
                params={"limit": periods, "type": "quarterly"},
            )
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                return data[:periods]
            elif isinstance(data, dict) and "data" in data:
                return data["data"][:periods]

            return []
        except httpx.HTTPError as e:
            logger.error("SEC API request failed for %s: %s", symbol, e)
            return []

    def fetch_company_info(self, symbol: str) -> dict:
        """Fetch company profile information."""
        try:
            response = self.client.get(f"/v1/companies/{symbol}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to fetch company info for %s: %s", symbol, e)
            return {}

    def close(self):
        """Close HTTP client."""
        self.client.close()


def main():
    parser = argparse.ArgumentParser(description="Fetch financial data from SEC API Portal")
    parser.add_argument("--symbol", required=True, help="Stock symbol (e.g., PTT)")
    parser.add_argument("--periods", type=int, default=8, help="Number of quarters (default: 8)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    client = SECApiClient()
    try:
        result = client.fetch(args.symbol, periods=args.periods)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    main()
