"""Fundamental analysis — financial statement analysis, ratios, valuation."""

import argparse
import json
import logging

logger = logging.getLogger(__name__)


def compute_ratios(financials: list[dict]) -> dict:
    """Compute financial ratios from quarterly financial statements.

    Args:
        financials: List of quarterly financial statement dicts from SEC API.

    Returns:
        Dict with profitability, leverage, liquidity, and valuation ratios.
    """
    if not financials:
        return {"error": "No financial data"}

    latest = financials[0]  # Most recent quarter

    # Extract values (keys depend on SEC API response format)
    total_assets = latest.get("total_assets", 0) or 0
    total_liabilities = latest.get("total_liabilities", 0) or 0
    total_equity = latest.get("total_equity", 0) or 0
    revenue = latest.get("revenue", 0) or 0
    net_income = latest.get("net_income", 0) or 0
    current_assets = latest.get("current_assets", 0) or 0
    current_liabilities = latest.get("current_liabilities", 0) or 0

    ratios = {
        "profitability": {
            "roe": _safe_divide(net_income, total_equity) * 100,
            "roa": _safe_divide(net_income, total_assets) * 100,
            "net_margin": _safe_divide(net_income, revenue) * 100,
        },
        "leverage": {
            "de_ratio": _safe_divide(total_liabilities, total_equity),
            "debt_to_assets": _safe_divide(total_liabilities, total_assets),
        },
        "liquidity": {
            "current_ratio": _safe_divide(current_assets, current_liabilities),
        },
    }

    # QoQ profit growth
    if len(financials) >= 2:
        prev_income = financials[1].get("net_income", 0) or 0
        ratios["growth"] = {
            "profit_qoq_pct": _safe_divide(net_income - prev_income, abs(prev_income)) * 100
            if prev_income != 0 else None,
        }

    # YoY comparison (4 quarters back)
    if len(financials) >= 5:
        yoy_income = financials[4].get("net_income", 0) or 0
        ratios["growth"]["profit_yoy_pct"] = (
            _safe_divide(net_income - yoy_income, abs(yoy_income)) * 100
            if yoy_income != 0 else None
        )

    return ratios


def grade_stock(ratios: dict, fscore: int) -> str:
    """Assign a letter grade (A-F) based on financial health.

    Args:
        ratios: Financial ratios dict
        fscore: Piotroski F-Score (0-9)

    Returns:
        Grade string: 'A', 'B', 'C', 'D', or 'F'
    """
    score = 0

    # F-Score contribution (0-30 points)
    score += min(30, fscore * 3.3)

    # ROE contribution (0-20 points)
    roe = ratios.get("profitability", {}).get("roe", 0)
    if roe > 15:
        score += 20
    elif roe > 10:
        score += 15
    elif roe > 5:
        score += 10

    # D/E ratio (0-20 points)
    de = ratios.get("leverage", {}).get("de_ratio", 99)
    if de < 0.5:
        score += 20
    elif de < 1.0:
        score += 15
    elif de < 2.0:
        score += 10

    # Profit growth (0-15 points)
    growth = ratios.get("growth", {}).get("profit_yoy_pct")
    if growth is not None:
        if growth > 20:
            score += 15
        elif growth > 10:
            score += 10
        elif growth > 0:
            score += 5

    # Current ratio (0-15 points)
    cr = ratios.get("liquidity", {}).get("current_ratio", 0)
    if cr > 2.0:
        score += 15
    elif cr > 1.5:
        score += 10
    elif cr > 1.0:
        score += 5

    if score >= 80:
        return "A"
    elif score >= 65:
        return "B"
    elif score >= 50:
        return "C"
    elif score >= 35:
        return "D"
    return "F"


def _safe_divide(numerator: float, denominator: float) -> float:
    """Safe division that returns 0 on divide-by-zero."""
    if denominator == 0:
        return 0.0
    return numerator / denominator


def main():
    parser = argparse.ArgumentParser(description="Fundamental analysis computation")
    parser.add_argument("--symbol", required=True, help="Stock symbol")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    from scrapers.sec_api_client import SECApiClient

    client = SECApiClient()
    financials = client.fetch(args.symbol, periods=8)
    client.close()

    if financials:
        ratios = compute_ratios(financials)
        print(json.dumps(ratios, indent=2, ensure_ascii=False))
    else:
        print(json.dumps({"error": "No data available"}))


if __name__ == "__main__":
    main()
