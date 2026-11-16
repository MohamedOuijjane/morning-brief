"""Deadlines from DEADLINES_JSON (secret), a local file or the example file."""

from datetime import date, timedelta
from typing import Any

from brief import config, utils

DEADLINES_HEADER_PREFIX = "📅 <b>Échéances"
TOMORROW_DEADLINES_HEADER = "⏰ <b>À rendre demain</b>"


def load_deadlines() -> list[dict[str, Any]]:
    try:
        return utils.load_json(
            config.DEADLINES_JSON, config.DEADLINES_FILE, config.DEADLINES_FALLBACK_FILE
        )
    except FileNotFoundError:
        return []


def deadlines_between(start: date, end: date) -> list[tuple[date, str]]:
    """(due date, title) for deadlines in [start, end], sorted by date."""
    return sorted(
        (due, item["title"])
        for item in load_deadlines()
        if start <= (due := date.fromisoformat(item["date"])) <= end
    )


def when_label(days_left: int) -> str:
    if days_left == 0:
        return "AUJOURD'HUI"
    if days_left == 1:
        return "demain"
    return f"dans {days_left} jours"


def urgency_marker(days_left: int) -> str:
    return "🔴" if days_left <= 2 else "🟡" if days_left <= 7 else "🟢"


def get_deadlines() -> str:
    start = utils.today()
    upcoming = deadlines_between(start, start + timedelta(days=config.DEADLINES_DAYS))
    header = f"{DEADLINES_HEADER_PREFIX} ({config.DEADLINES_DAYS} prochains jours)</b>"
    if not upcoming:
        return f"{header}\nRien à signaler. 🎉"
    lines = [header]
    for due, title in upcoming:
        days_left = (due - start).days
        lines.append(
            f"{urgency_marker(days_left)} {utils.escape(title)} : "
            f"{utils.format_short_date(due)} ({when_label(days_left)})"
        )
    return "\n".join(lines)


def get_tomorrow_deadlines() -> str | None:
    tomorrow = utils.today() + timedelta(days=1)
    titles = sorted(title for _, title in deadlines_between(tomorrow, tomorrow))
    if not titles:
        return None  # nothing due tomorrow: omit the section
    return "\n".join([TOMORROW_DEADLINES_HEADER] + [f"• {utils.escape(t)}" for t in titles])
