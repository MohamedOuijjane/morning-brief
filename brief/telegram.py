"""Telegram Bot API: send a message and split long ones."""

import requests

from brief import config

TELEGRAM_LIMIT = 4096  # max characters per Telegram message


def split_messages(sections: list[str], limit: int = TELEGRAM_LIMIT) -> list[str]:
    """Join sections into as few messages as possible, splitting only at
    section boundaries. A single oversized section is cut as a last resort."""
    messages: list[str] = []
    current = ""
    for section in sections:
        while len(section) > limit:  # should not happen with normal content
            if current:
                messages.append(current)
                current = ""
            messages.append(section[:limit])
            section = section[limit:]
        candidate = f"{current}\n\n{section}" if current else section
        if len(candidate) <= limit:
            current = candidate
        else:
            messages.append(current)
            current = section
    if current:
        messages.append(current)
    return messages


def send(message: str) -> None:
    if not config.TELEGRAM_TOKEN or not config.TELEGRAM_CHAT_ID:
        raise RuntimeError("TELEGRAM_TOKEN and TELEGRAM_CHAT_ID must be set")
    resp = requests.post(
        f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
        json={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=15,
    )
    if not resp.ok:
        # Do not echo the URL: it contains the bot token.
        raise RuntimeError(f"Telegram API error {resp.status_code}: {resp.text}")
