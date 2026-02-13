"""LINE Notify API wrapper — sends alert messages via LINE."""

import logging
import os

import requests

logger = logging.getLogger(__name__)

LINE_NOTIFY_URL = "https://notify-api.line.me/api/notify"


def send_line_notification(message: str, token: str | None = None) -> dict:
    """Send a notification via LINE Notify.

    Args:
        message: Message text to send (max 1000 chars)
        token: LINE Notify token (falls back to env var)

    Returns:
        Dict with status and response info.
    """
    token = token or os.getenv("LINE_NOTIFY_TOKEN", "")
    if not token:
        logger.warning("LINE_NOTIFY_TOKEN not set, skipping notification")
        return {"status": "skipped", "reason": "No token configured"}

    # LINE Notify has a 1000 char limit
    if len(message) > 1000:
        message = message[:997] + "..."

    headers = {"Authorization": f"Bearer {token}"}
    data = {"message": message}

    try:
        response = requests.post(LINE_NOTIFY_URL, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        logger.info("LINE notification sent successfully")
        return {"status": "sent", "http_status": response.status_code}
    except requests.RequestException as e:
        logger.error("LINE notification failed: %s", e)
        return {"status": "failed", "error": str(e)}
