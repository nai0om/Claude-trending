"""Action Plan Agent — generates daily BUY/SELL/HOLD recommendations with position sizing and risk checks."""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Risk management imports (lazy to avoid circular deps)
_risk_manager = None


def _get_risk_manager():
    global _risk_manager
    if _risk_manager is None:
        from analysis import risk_manager
        _risk_manager = risk_manager
    return _risk_manager


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

    rm = _get_risk_manager()
    watchlist = load_watchlist()
    actions = []
    risk_warnings = []

    # Check daily loss halt before processing any BUY
    daily_halt = rm.check_daily_loss_halt()
    halt_active = daily_halt.get("halt_active", False)
    if halt_active:
        risk_warnings.append(daily_halt["message"])

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
            action_risk_warnings = []

            if action == "BUY":
                # Override to HOLD if daily loss halt is active
                if halt_active:
                    action = "HOLD"
                    action_risk_warnings.append("Daily loss halt active — BUY overridden to HOLD")
                else:
                    amount = calculate_position_size(
                        budget=budget,
                        conviction_score=score,
                        current_price=analysis.get("technical", {}).get("close", 0),
                    )
                    # Check position limits
                    if amount > 0:
                        limit_check = rm.check_position_limits(symbol, amount)
                        if not limit_check["allowed"]:
                            action_risk_warnings.extend(limit_check["warnings"])
                            if limit_check["allowed_amount"] > 0:
                                amount = limit_check["allowed_amount"]
                                action_risk_warnings.append(
                                    f"Amount reduced to {amount:,.0f} THB due to position limits"
                                )
                            else:
                                action = "HOLD"
                                amount = 0.0
                                action_risk_warnings.append("BUY blocked — position limits exceeded")

            reasoning = _build_reasoning(analysis)
            if action_risk_warnings:
                reasoning += " | RISK: " + "; ".join(action_risk_warnings)
                risk_warnings.extend(action_risk_warnings)

            actions.append({
                "symbol": symbol,
                "name": stock["name"],
                "sector": stock["sector"],
                "action": action,
                "composite_score": score,
                "amount_thb": round(amount, 2),
                "reasoning": reasoning,
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
        "risk_warnings": risk_warnings,
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
