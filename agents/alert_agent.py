"""Alert Agent — decides and dispatches alerts via LINE and Telegram."""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

DISCLAIMER = "ข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำในการลงทุน"


def load_thresholds() -> dict:
    """Load alert thresholds from config."""
    config_path = Path(__file__).parent.parent / "config" / "thresholds.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def determine_alert_type(composite_score: float, indicators: dict, thresholds: dict) -> str | None:
    """Determine if an alert should be triggered and what type.

    Args:
        composite_score: Combined score from -100 to +100
        indicators: Dict with RSI, sentiment, volume_ratio, etc.
        thresholds: Alert thresholds from config

    Returns:
        Alert type ('BUY', 'SELL', 'WATCH') or None.
    """
    rsi = indicators.get("rsi", 50)
    sentiment = indicators.get("sentiment_score", 0)
    volume_ratio = indicators.get("volume_ratio", 1.0)

    buy = thresholds["buy"]
    if (composite_score > buy["composite_min"]
            and rsi < buy["rsi_max"]
            and sentiment > buy["sentiment_min"]
            and volume_ratio > buy["volume_ratio_min"]):
        return "BUY"

    sell = thresholds["sell"]
    if (composite_score < sell["composite_max"]
            and rsi > sell["rsi_min"]
            and sentiment < sell["sentiment_max"]):
        return "SELL"

    watch = thresholds["watch"]
    if (volume_ratio > watch["volume_ratio_min"]
            or abs(indicators.get("price_change_pct", 0)) > watch["intraday_price_move_pct"]):
        return "WATCH"

    return None


def determine_confidence(sources_count: int, thresholds: dict) -> str:
    """Determine confidence level based on number of data sources."""
    conf = thresholds["confidence"]
    if sources_count >= conf["high_min_sources"]:
        return "High"
    elif sources_count >= conf["medium_min_sources"]:
        return "Medium"
    return "Low"


def format_alert(alert_type: str, symbol: str, data: dict, confidence: str) -> str:
    """Format alert message from template."""
    template_dir = Path(__file__).parent.parent / "alerts" / "templates"
    template_map = {
        "BUY": "buy_alert.md",
        "SELL": "sell_alert.md",
        "WATCH": "watchlist.md",
        "FUNDAMENTAL": "fundamental_alert.md",
    }

    template_file = template_dir / template_map.get(alert_type, "watchlist.md")
    if template_file.exists():
        template = template_file.read_text()
        # Simple placeholder replacement
        msg = template.replace("{{symbol}}", symbol)
        msg = msg.replace("{{confidence}}", confidence)
        msg = msg.replace("{{disclaimer}}", DISCLAIMER)
        return msg

    return f"[{alert_type}] {symbol} — Confidence: {confidence}\n{DISCLAIMER}"


def send_alert(alert_type: str, symbol: str, data: dict) -> dict:
    """Send alert via configured channels."""
    from alerts.line_notify import send_line_notification
    from alerts.telegram_bot import send_telegram_message

    thresholds = load_thresholds()
    confidence = determine_confidence(data.get("sources_count", 1), thresholds)
    message = format_alert(alert_type, symbol, data, confidence)

    results = {"line": None, "telegram": None}

    try:
        results["line"] = send_line_notification(message)
    except Exception as e:
        logger.error("LINE notification failed: %s", e)
        results["line"] = {"error": str(e)}

    try:
        results["telegram"] = send_telegram_message(message)
    except Exception as e:
        logger.error("Telegram notification failed: %s", e)
        results["telegram"] = {"error": str(e)}

    return {
        "alert_type": alert_type,
        "symbol": symbol,
        "confidence": confidence,
        "sent_at": datetime.now().isoformat(),
        "delivery": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Send trading alerts")
    parser.add_argument("--symbol", required=True, help="Stock symbol")
    parser.add_argument("--type", choices=["BUY", "SELL", "WATCH", "FUNDAMENTAL"], required=True)
    parser.add_argument("--data", type=str, help="JSON data string")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    data = json.loads(args.data) if args.data else {}
    result = send_alert(args.type, args.symbol, data)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
