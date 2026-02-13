"""Action Plan Agent — generates daily BUY/SELL/HOLD recommendations with position sizing."""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def generate_action_plan(budget: float = 100000.0) -> dict:
    """Generate daily action plan for all watchlist stocks.

    Runs analysis on each stock and recommends BUY/SELL/HOLD
    with suggested allocation amounts based on budget and conviction.

    Args:
        budget: Available cash for new positions (THB)

    Returns:
        Dict with per-stock recommendations and amounts.
    """
    from agents.orchestrator import load_watchlist, analyze_single
    from analysis.position_sizing import calculate_position_size

    watchlist = load_watchlist()
    actions = []

    for stock in watchlist:
        symbol = stock["symbol"]
        logger.info("Analyzing %s for action plan...", symbol)

        try:
            analysis = analyze_single(symbol)
            score = analysis.get("scoring", {}).get("composite_score", 0)

            # Determine action
            if score > 30:
                action = "BUY"
            elif score < -30:
                action = "SELL"
            else:
                action = "HOLD"

            # Calculate position size for BUY signals
            amount = 0.0
            if action == "BUY":
                amount = calculate_position_size(
                    budget=budget,
                    conviction_score=score,
                    current_price=analysis.get("technical", {}).get("close", 0),
                )

            actions.append({
                "symbol": symbol,
                "name": stock["name"],
                "sector": stock["sector"],
                "action": action,
                "composite_score": score,
                "amount_thb": round(amount, 2),
                "reasoning": _build_reasoning(analysis),
            })
        except Exception as e:
            logger.error("Failed to analyze %s: %s", symbol, e)
            actions.append({
                "symbol": symbol,
                "name": stock["name"],
                "action": "SKIP",
                "error": str(e),
            })

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "generated_at": datetime.now().isoformat(),
        "budget": budget,
        "actions": actions,
        "summary": _summarize(actions),
    }


def _build_reasoning(analysis: dict) -> str:
    """Build brief reasoning text from analysis results."""
    parts = []
    tech = analysis.get("technical", {})
    indicators = tech.get("indicators", {})
    if indicators.get("rsi"):
        parts.append(f"RSI={indicators['rsi']}")
    signals = tech.get("signals", [])
    if signals:
        parts.append(", ".join(signals))
    return " | ".join(parts) if parts else "Insufficient data"


def _summarize(actions: list[dict]) -> dict:
    """Summarize action plan."""
    buys = [a for a in actions if a.get("action") == "BUY"]
    sells = [a for a in actions if a.get("action") == "SELL"]
    holds = [a for a in actions if a.get("action") == "HOLD"]
    return {
        "buy_count": len(buys),
        "sell_count": len(sells),
        "hold_count": len(holds),
        "total_buy_amount": sum(a.get("amount_thb", 0) for a in buys),
    }


def main():
    parser = argparse.ArgumentParser(description="Generate daily trading action plan")
    parser.add_argument("--budget", type=float, default=100000, help="Available budget in THB")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    plan = generate_action_plan(budget=args.budget)
    print(json.dumps(plan, default=str, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
