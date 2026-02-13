"""Composite scoring — combines all analysis scores with configurable weights."""

from pathlib import Path

import yaml


def load_weights() -> dict:
    """Load scoring weights from config."""
    config_path = Path(__file__).parent.parent / "config" / "thresholds.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config["composite_scoring"]["weights"]


def load_fundamental_weights() -> dict:
    """Load fundamental sub-scoring weights."""
    config_path = Path(__file__).parent.parent / "config" / "thresholds.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config["fundamental_sub_weights"]


def compute_composite_score(
    technical_score: float = 0,
    sentiment_score: float = 0,
    volume_score: float = 0,
    fundamental_score: float = 0,
    news_score: float = 0,
    fund_flow_score: float = 0,
) -> dict:
    """Compute weighted composite score.

    All input scores should be in range -100 to +100.

    Returns:
        Dict with composite score, breakdown, and signal.
    """
    weights = load_weights()

    scores = {
        "technical": technical_score,
        "sentiment": sentiment_score,
        "volume": volume_score,
        "fundamental": fundamental_score,
        "news": news_score,
        "fund_flow": fund_flow_score,
    }

    composite = sum(scores[k] * weights.get(k, 0) for k in scores)
    composite = max(-100, min(100, composite))

    # Determine signal
    if composite > 60:
        signal = "STRONG BUY"
    elif composite > 30:
        signal = "BUY"
    elif composite > -30:
        signal = "HOLD"
    elif composite > -60:
        signal = "SELL"
    else:
        signal = "STRONG SELL"

    return {
        "composite_score": round(composite, 2),
        "signal": signal,
        "breakdown": {k: round(v, 2) for k, v in scores.items()},
        "weights": weights,
    }


def compute_fundamental_subscore(
    profitability_score: float = 0,
    financial_health_score: float = 0,
    cash_flow_score: float = 0,
    valuation_score: float = 0,
    piotroski_score: float = 0,
) -> float:
    """Compute weighted fundamental sub-score.

    All inputs should be in range -100 to +100.

    Returns:
        Fundamental score from -100 to +100.
    """
    weights = load_fundamental_weights()

    scores = {
        "profitability": profitability_score,
        "financial_health": financial_health_score,
        "cash_flow": cash_flow_score,
        "valuation": valuation_score,
        "piotroski": piotroski_score,
    }

    result = sum(scores[k] * weights.get(k, 0) for k in scores)
    return max(-100, min(100, round(result, 2)))
