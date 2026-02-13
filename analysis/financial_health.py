"""Financial Health — Piotroski F-Score calculation (9 criteria, score 0-9)."""

import argparse
import json
import logging

logger = logging.getLogger(__name__)


def compute_fscore(financials: list[dict]) -> dict:
    """Compute Piotroski F-Score from financial statements.

    Nine binary criteria covering:
    - Profitability (4 points): ROA, Operating CF, ROA delta, CF quality
    - Capital Structure (3 points): Leverage delta, Liquidity delta, Dilution
    - Efficiency (2 points): Gross margin delta, Asset turnover delta

    Args:
        financials: List of quarterly financial statements (newest first).
                   Needs at least 2 periods for deltas.

    Returns:
        Dict with total score (0-9), breakdown, and interpretation.
    """
    if len(financials) < 2:
        return {"score": None, "error": "Need at least 2 periods", "breakdown": {}}

    current = financials[0]
    previous = financials[1]

    breakdown = {}
    score = 0

    # === PROFITABILITY (4 points) ===

    # 1. ROA > 0 (positive net income / total assets)
    roa = _safe_divide(current.get("net_income", 0), current.get("total_assets", 1))
    breakdown["roa_positive"] = 1 if roa > 0 else 0
    score += breakdown["roa_positive"]

    # 2. Operating Cash Flow > 0
    ocf = current.get("operating_cash_flow", 0) or 0
    breakdown["ocf_positive"] = 1 if ocf > 0 else 0
    score += breakdown["ocf_positive"]

    # 3. ROA increasing (current > previous)
    prev_roa = _safe_divide(previous.get("net_income", 0), previous.get("total_assets", 1))
    breakdown["roa_increasing"] = 1 if roa > prev_roa else 0
    score += breakdown["roa_increasing"]

    # 4. Cash flow quality (OCF > net income = accruals quality)
    net_income = current.get("net_income", 0) or 0
    breakdown["cf_quality"] = 1 if ocf > net_income else 0
    score += breakdown["cf_quality"]

    # === CAPITAL STRUCTURE (3 points) ===

    # 5. Leverage decreasing (D/E ratio)
    curr_de = _safe_divide(
        current.get("total_liabilities", 0), current.get("total_equity", 1)
    )
    prev_de = _safe_divide(
        previous.get("total_liabilities", 0), previous.get("total_equity", 1)
    )
    breakdown["leverage_decreasing"] = 1 if curr_de < prev_de else 0
    score += breakdown["leverage_decreasing"]

    # 6. Current ratio increasing
    curr_cr = _safe_divide(
        current.get("current_assets", 0), current.get("current_liabilities", 1)
    )
    prev_cr = _safe_divide(
        previous.get("current_assets", 0), previous.get("current_liabilities", 1)
    )
    breakdown["liquidity_increasing"] = 1 if curr_cr > prev_cr else 0
    score += breakdown["liquidity_increasing"]

    # 7. No share dilution (shares outstanding not increased)
    curr_shares = current.get("shares_outstanding", 0) or 0
    prev_shares = previous.get("shares_outstanding", 0) or 0
    breakdown["no_dilution"] = 1 if curr_shares <= prev_shares else 0
    score += breakdown["no_dilution"]

    # === EFFICIENCY (2 points) ===

    # 8. Gross margin increasing
    curr_margin = _safe_divide(
        current.get("gross_profit", 0), current.get("revenue", 1)
    )
    prev_margin = _safe_divide(
        previous.get("gross_profit", 0), previous.get("revenue", 1)
    )
    breakdown["margin_increasing"] = 1 if curr_margin > prev_margin else 0
    score += breakdown["margin_increasing"]

    # 9. Asset turnover increasing
    curr_turnover = _safe_divide(current.get("revenue", 0), current.get("total_assets", 1))
    prev_turnover = _safe_divide(previous.get("revenue", 0), previous.get("total_assets", 1))
    breakdown["turnover_increasing"] = 1 if curr_turnover > prev_turnover else 0
    score += breakdown["turnover_increasing"]

    # Interpretation
    if score >= 7:
        interpretation = "Strong"
    elif score >= 4:
        interpretation = "Moderate"
    else:
        interpretation = "Weak"

    return {
        "score": score,
        "max_score": 9,
        "interpretation": interpretation,
        "breakdown": breakdown,
    }


def _safe_divide(numerator: float, denominator: float) -> float:
    """Safe division returning 0 on divide-by-zero."""
    if not denominator:
        return 0.0
    return (numerator or 0) / denominator


def main():
    parser = argparse.ArgumentParser(description="Compute Piotroski F-Score")
    parser.add_argument("--symbol", required=True, help="Stock symbol")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    from scrapers.sec_api_client import SECApiClient

    client = SECApiClient()
    financials = client.fetch(args.symbol, periods=8)
    client.close()

    if financials:
        result = compute_fscore(financials)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(json.dumps({"error": "No financial data available"}))


if __name__ == "__main__":
    main()
