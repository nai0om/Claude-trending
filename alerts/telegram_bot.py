"""Telegram Bot API wrapper — sends alert messages via Telegram."""

import logging
import os

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram_message(
    message: str,
    token: str | None = None,
    chat_id: str | None = None,
) -> dict:
    """Send a message via Telegram Bot.

    Args:
        message: Message text to send (supports Markdown)
        token: Telegram Bot token (falls back to env var)
        chat_id: Target chat ID (falls back to env var)

    Returns:
        Dict with status and response info.
    """
    token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        logger.warning("Telegram credentials not set, skipping notification")
        return {"status": "skipped", "reason": "No token or chat_id configured"}

    url = TELEGRAM_API_URL.format(token=token)
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        logger.info("Telegram message sent successfully")
        return {"status": "sent", "http_status": response.status_code}
    except requests.RequestException as e:
        logger.error("Telegram message failed: %s", e)
        return {"status": "failed", "error": str(e)}
