"""WhatsApp notification service via CallMeBot API (free tier)."""

from __future__ import annotations

import logging
import os
from urllib.parse import quote

import requests

logger = logging.getLogger("api")

_CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"


def send_whatsapp(phone: str, message: str) -> bool:
    """Send a WhatsApp message via CallMeBot API.

    Returns True on success, False on failure (never raises).
    The procurement head must have registered with CallMeBot first
    (send "join <code>" to +34 644 71 81 97 on WhatsApp).
    """
    api_key = os.getenv("WHATSAPP_API_KEY", "")
    if not api_key:
        logger.warning("WHATSAPP_API_KEY not configured — skipping WhatsApp notification")
        return False

    if not phone:
        logger.warning("No phone number for procurement user — skipping WhatsApp notification")
        return False

    clean_phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean_phone.startswith("+"):
        clean_phone = "+91" + clean_phone

    try:
        resp = requests.get(
            _CALLMEBOT_URL,
            params={
                "phone": clean_phone,
                "text": message,
                "apikey": api_key,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            logger.info("WhatsApp notification sent to %s", clean_phone)
            return True
        else:
            logger.error("CallMeBot API returned %d: %s", resp.status_code, resp.text[:200])
            return False
    except Exception as exc:
        logger.error("Failed to send WhatsApp notification: %s", exc)
        return False


def format_urgent_inquiry_message(
    title: str,
    inquiry_type: str,
    created_by: str,
    lead_id: str,
    company_name: str | None,
    description: str | None,
) -> str:
    """Format an urgent inquiry notification message."""
    lines = [
        "🚨 *URGENT Inquiry*",
        "",
        f"*{title}*",
        f"Type: {inquiry_type}",
        f"From: {created_by}",
        f"Lead: {lead_id}",
    ]
    if company_name:
        lines.append(f"Company: {company_name}")
    if description:
        lines.append(f"Details: {description[:200]}")
    lines.append("")
    lines.append("Please respond ASAP.")
    return "\n".join(lines)
