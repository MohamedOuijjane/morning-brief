"""Dates, French formatting and data loading shared by all sections."""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from brief import config

# French day/month names (Monday = 0), independent of the system locale.
DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
DAYS_SHORT = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]
MONTHS_SHORT = [
    "janv.", "févr.", "mars", "avr.", "mai", "juin",
    "juil.", "août", "sept.", "oct.", "nov.", "déc.",
]


def now() -> datetime:
    """Current time in the configured timezone (patched in tests)."""
    return datetime.now(ZoneInfo(config.TIMEZONE))


def today() -> date:
    return now().date()


def format_long_date(d: date) -> str:
    """e.g. 'lundi 16 novembre 2026'."""
    return f"{DAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]} {d.year}"


def format_short_date(d: date) -> str:
    """e.g. 'mar. 17 nov.'."""
    return f"{DAYS_SHORT[d.weekday()]} {d.day} {MONTHS_SHORT[d.month - 1]}"


def fr_number(value: object) -> str:
    """French decimal separator: 10.9 -> '10,9'."""
    return str(value).replace(".", ",")


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'s' if n > 1 else ''}"


def escape(text: str) -> str:
    """Escape text for Telegram's HTML parse mode."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def resolve(name: str) -> Path:
    path = Path(name)
    return path if path.is_absolute() else config.ROOT / path


def load_json(raw: str, *files: str) -> Any:
    """Load JSON from raw text (a secret) if set, else from the first existing
    file. Raises FileNotFoundError if nothing is available."""
    if raw:
        return json.loads(raw)
    for name in files:
        path = resolve(name)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError("no data source available")


def pick_by_date(items: list[Any], day: date) -> Any:
    """Deterministic daily pick: same item all day, cycling over time."""
    return items[day.toordinal() % len(items)]
