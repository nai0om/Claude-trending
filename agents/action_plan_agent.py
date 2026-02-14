"""Action Plan Agent — full-pipeline daily BUY/SELL/HOLD with all data sources and risk checks."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

# Lazy imports to avoid circular deps
_risk_manager = None


def _get_risk_manager():
    global _risk_manager
    if _risk_manager is None:
        from analysis import risk_manager
        _risk_manager = risk_manager
    return _risk_manager


def _run_full_analysis(symbol: str) -> dict:
    """Run ALL agents for a single stock with graceful fallbacks.

    Runs: technical, sentiment, fundamental, news.
    Each agent can fail independently without killing the whole analysis.
    """
    result = {"symbol": symbol, "analyzed_at": datetime.now().isoformat()}

    # 1. Technical (price, RSI, MACD, Bollinger)
    try:
        from agents.technical_agent import compute_indicators
        result["technical"] = compute_indicators(symbol)
    except Exception as e:
        logger.warning("Technical failed for %s: %s", symbol, e)
        # Fallback: basic price data via yfinance
        try:
            import yfinance as yf
            t = yf.Ticker(f"{symbol}.BK")
            h = t.history(period="6mo")
            if not h.empty:
                last = h.iloc[-1]
                vol_avg = h["Volume"].tail(20).mean()
                result["technical"] = {
                    "symbol": symbol,
                    "close": round(float(last["Close"]), 2),
                    "indicators": {},
                    "signals": [],
                    "fallback": True,
                    "volume": int(last["Volume"]),
                    "volume_ratio": round(float(last["Volume"] / vol_avg), 2) if vol_avg > 0 else 0,
                }
            else:
                result["technical"] = {"error": str(e)}
        except Exception:
            result["technical"] = {"error": str(e)}

    # 2. Sentiment (Search Center API — social media, webboards)
    try:
        from agents.sentiment_agent import analyze_sentiment
        result["sentiment"] = analyze_sentiment(symbol)
    except Exception as e:
        logger.warning("Sentiment failed for %s: %s", symbol, e)
        result["sentiment"] = {"error": str(e), "sentiment_score": 0}

    # 3. Fundamental (SEC API — financial ratios, F-Score)
    try:
        from agents.fundamental_agent import analyze_fundamental
        result["fundamental"] = analyze_fundamental(symbol, quick=True)
    except Exception as e:
        logger.warning("Fundamental failed for %s: %s", symbol, e)
        result["fundamental"] = {"error": str(e)}

    # 4. News (Search Center API — news articles, webboard)
    try:
        from agents.news_agent import analyze_news
        result["news"] = analyze_news(symbol)
    except Exception as e:
        logger.warning("News failed for %s: %s", symbol, e)
        result["news"] = {"error": str(e)}

    # 5. Compute composite score
    try:
        from agents.orchestrator import compute_composite_score
        result["scoring"] = compute_composite_score(result)
    except Exception as e:
        logger.warning("Scoring failed for %s: %s", symbol, e)
        result["scoring"] = {"composite_score": 0, "breakdown": {}, "error": str(e)}

    return result


def _build_reasoning(analysis: dict) -> str:
    """Build comprehensive reasoning from ALL data sources."""
    parts = []

    # Technical signals
    tech = analysis.get("technical", {})
    indicators = tech.get("indicators", {})
    if indicators.get("rsi") is not None:
        parts.append(f"RSI={indicators['rsi']}")
    if indicators.get("macd_histogram") is not None:
        direction = "bullish" if indicators["macd_histogram"] > 0 else "bearish"
        parts.append(f"MACD {direction}")
    signals = tech.get("signals", [])
    if signals:
        parts.append(", ".join(signals))
    vol_ratio = tech.get("volume_ratio", 0)
    if vol_ratio and vol_ratio > 1.5:
        parts.append(f"Vol={vol_ratio}x avg")

    # Sentiment
    sent = analysis.get("sentiment", {})
    if "error" not in sent:
        score = sent.get("sentiment_score", 0)
        label = sent.get("label", "")
        mentions = sent.get("total_mentions", 0)
        confidence = sent.get("confidence", "")
        if mentions > 0:
            parts.append(f"Sentiment={label}({score:+.2f}, {mentions} mentions, {confidence})")

    # Fundamental
    fund = analysis.get("fundamental", {})
    if "error" not in fund:
        fscore = fund.get("fscore", {})
        if isinstance(fscore, dict) and fscore.get("score") is not None:
            parts.append(f"F-Score={fscore['score']}/9")
        ratios = fund.get("ratios", {})
        if isinstance(ratios, dict):
            roe = ratios.get("roe")
            de = ratios.get("debt_to_equity")
            if roe is not None:
                parts.append(f"ROE={roe:.1%}" if isinstance(roe, float) else f"ROE={roe}")
            if de is not None:
                parts.append(f"D/E={de:.2f}" if isinstance(de, float) else f"D/E={de}")

    # News
    news = analysis.get("news", {})
    if "error" not in news:
        count = news.get("news_count", 0)
        if count > 0:
            ns = news.get("news_sentiment", {})
            parts.append(f"News={count} articles (pos={ns.get('positive', 0)}, neg={ns.get('negative', 0)})")

    # Data sources available
    sources = []
    if "error" not in tech:
        sources.append("T")
    if "error" not in sent and sent.get("total_mentions", 0) > 0:
        sources.append("S")
    if "error" not in fund:
        sources.append("F")
    if "error" not in news and news.get("news_count", 0) > 0:
        sources.append("N")
    if sources:
        parts.append(f"Sources: {'/'.join(sources)}")

    return " | ".join(parts) if parts else "Insufficient data"


def generate_action_plan(budget: float = 100000.0) -> dict:
    """Generate daily action plan using ALL analysis agents.

    Full pipeline per stock: technical + sentiment + fundamental + news
    → composite score → position sizing → risk checks.

    Args:
        budget: Available cash for new positions (THB)

    Returns:
        Dict with per-stock recommendations and amounts.
    """
    from analysis.position_sizing import calculate_position_size

    rm = _get_risk_manager()

    # Load watchlist
    watchlist_path = Path(__file__).parent.parent / "data" / "watchlist.json"
    with open(watchlist_path) as f:
        watchlist = json.load(f)["watchlist"]

    actions = []
    risk_warnings = []

    # Check daily loss halt before processing any BUY
    daily_halt = rm.check_daily_loss_halt()
    halt_active = daily_halt.get("halt_active", False)
    if halt_active:
        risk_warnings.append(daily_halt["message"])

    for stock in watchlist:
        symbol = stock["symbol"]
        logger.info("Full analysis: %s (%s)...", symbol, stock["name"])

        try:
            # Run ALL agents
            analysis = _run_full_analysis(symbol)
            score = analysis.get("scoring", {}).get("composite_score", 0)
            breakdown = analysis.get("scoring", {}).get("breakdown", {})

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
                "composite_score": round(score, 2),
                "score_breakdown": breakdown,
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


def _summarize(actions: list) -> dict:
    """Summarize action plan."""
    buys = [a for a in actions if a.get("action") == "BUY"]
    sells = [a for a in actions if a.get("action") == "SELL"]
    holds = [a for a in actions if a.get("action") == "HOLD"]
    skips = [a for a in actions if a.get("action") == "SKIP"]
    return {
        "buy_count": len(buys),
        "sell_count": len(sells),
        "hold_count": len(holds),
        "skip_count": len(skips),
        "total_buy_amount": sum(a.get("amount_thb", 0) for a in buys),
        "data_sources_used": ["technical", "sentiment", "fundamental", "news"],
    }


def main():
    parser = argparse.ArgumentParser(description="Generate daily trading action plan (full pipeline)")
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
