"""Fundamental Analysis Agent — financial statements, ratios, F-Score analysis."""

import argparse
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def analyze_fundamental(symbol: str, quick: bool = False) -> dict:
    """Run fundamental analysis on a SET stock.

    Args:
        symbol: SET ticker symbol (e.g., 'PTT')
        quick: If True, run quick scan (fewer quarters)

    Returns:
        Dict with financial ratios, F-Score, and grade.
    """
    from scrapers.sec_api_client import SECApiClient
    from analysis.fundamental import compute_ratios
    from analysis.financial_health import compute_fscore

    periods = 4 if quick else 8
    client = SECApiClient()
    financials = client.fetch(symbol, periods=periods)

    if not financials:
        return {
            "symbol": symbol,
            "error": "No financial data available",
        }

    ratios = compute_ratios(financials)
    fscore = compute_fscore(financials)

    return {
        "symbol": symbol,
        "analyzed_at": datetime.now().isoformat(),
        "mode": "quick" if quick else "deep",
        "periods_analyzed": periods,
        "ratios": ratios,
        "fscore": fscore,
        "financials_raw": financials,
    }


def main():
    parser = argparse.ArgumentParser(description="Fundamental analysis for SET stocks")
    parser.add_argument("--symbol", required=True, help="Stock symbol (e.g., PTT)")
    parser.add_argument("--quick", action="store_true", help="Quick scan mode (4 quarters)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    result = analyze_fundamental(args.symbol, quick=args.quick)
    print(json.dumps(result, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
