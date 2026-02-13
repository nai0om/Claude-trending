"""Orchestrator Agent — combines all sub-agent results into composite score and triggers alerts."""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def load_watchlist() -> list[dict]:
    """Load watchlist from JSON."""
    path = Path(__file__).parent.parent / "data" / "watchlist.json"
    with open(path) as f:
        return json.load(f)["watchlist"]


def load_weights() -> dict:
    """Load scoring weights from thresholds config."""
    path = Path(__file__).parent.parent / "config" / "thresholds.yaml"
    with open(path) as f:
        config = yaml.safe_load(f)
    return config["composite_scoring"]["weights"]


def run_analysis(symbol: str) -> dict:
    """Run all sub-agents and collect results for a single stock.

    Returns dict with each agent's output.
    """
    results = {"symbol": symbol, "analyzed_at": datetime.now().isoformat()}

    # Technical analysis
    try:
        from agents.technical_agent import compute_indicators
        results["technical"] = compute_indicators(symbol)
    except Exception as e:
        logger.error("Technical analysis failed for %s: %s", symbol, e)
        results["technical"] = {"error": str(e)}

    # Sentiment analysis
    try:
        from agents.sentiment_agent import analyze_sentiment
        results["sentiment"] = analyze_sentiment(symbol)
    except Exception as e:
        logger.error("Sentiment analysis failed for %s: %s", symbol, e)
        results["sentiment"] = {"error": str(e)}

    # Fundamental analysis
    try:
        from agents.fundamental_agent import analyze_fundamental
        results["fundamental"] = analyze_fundamental(symbol, quick=True)
    except Exception as e:
        logger.error("Fundamental analysis failed for %s: %s", symbol, e)
        results["fundamental"] = {"error": str(e)}

    # News analysis
    try:
        from agents.news_agent import analyze_news
        results["news"] = analyze_news(symbol)
    except Exception as e:
        logger.error("News analysis failed for %s: %s", symbol, e)
        results["news"] = {"error": str(e)}

    return results


def compute_composite_score(results: dict) -> dict:
    """Compute weighted composite score from all agent results.

    Returns dict with composite score (-100 to +100), breakdown, and signal.
    """
    weights = load_weights()
    scores = {}

    # Extract scores from each component (stub: returns 0 if no real data)
    technical = results.get("technical", {})
    if "error" not in technical:
        rsi = technical.get("indicators", {}).get("rsi", 50)
        # Map RSI to score: RSI<30 → positive, RSI>70 → negative
        if rsi is not None:
            scores["technical"] = max(-100, min(100, (50 - rsi) * 3))
        else:
            scores["technical"] = 0
    else:
        scores["technical"] = 0

    sentiment = results.get("sentiment", {})
    scores["sentiment"] = sentiment.get("sentiment_score", 0) * 100

    scores["volume"] = 0  # TODO: implement volume scoring
    scores["news"] = 0  # TODO: implement news impact scoring
    scores["fund_flow"] = 0  # TODO: implement fund flow scoring

    fundamental = results.get("fundamental", {})
    fscore = fundamental.get("fscore", {}).get("score", 5)
    scores["fundamental"] = (fscore - 5) * 25  # Map 0-9 → -125 to +100

    # Weighted composite
    composite = sum(scores[k] * weights.get(k, 0) for k in scores)
    composite = max(-100, min(100, composite))

    return {
        "composite_score": round(composite, 2),
        "breakdown": {k: round(v, 2) for k, v in scores.items()},
        "weights": weights,
    }


def analyze_single(symbol: str) -> dict:
    """Full analysis pipeline for a single stock."""
    logger.info("Analyzing %s...", symbol)
    results = run_analysis(symbol)
    scoring = compute_composite_score(results)
    results["scoring"] = scoring
    return results


def scan_watchlist() -> list[dict]:
    """Scan all watchlist stocks."""
    watchlist = load_watchlist()
    all_results = []
    for stock in watchlist:
        logger.info("Scanning %s (%s)...", stock["symbol"], stock["sector"])
        result = analyze_single(stock["symbol"])
        result["sector"] = stock["sector"]
        result["name"] = stock["name"]
        all_results.append(result)
    return all_results


def main():
    parser = argparse.ArgumentParser(description="Orchestrate SET stock analysis")
    parser.add_argument("--mode", choices=["analyze", "scan"], required=True)
    parser.add_argument("--symbol", help="Stock symbol (required for analyze mode)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    if args.mode == "analyze":
        if not args.symbol:
            parser.error("--symbol is required for analyze mode")
        result = analyze_single(args.symbol)
        print(json.dumps(result, default=str, ensure_ascii=False))
    elif args.mode == "scan":
        results = scan_watchlist()
        print(json.dumps({"scan_results": results, "count": len(results)}, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
