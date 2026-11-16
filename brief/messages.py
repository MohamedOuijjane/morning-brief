"""Assemble the morning and evening messages from independent sections."""

import sys
from collections.abc import Callable

from brief import calendar, config, deadlines, notes, quran, utils, weather, weekly, word

# A source returns a section, or None when it is not configured / not needed.
Source = Callable[[], str | None]

# Names used in the fallback line when a source fails.
SOURCE_LABELS: dict[str, str] = {
    "get_verse": "Verset du jour",
    "get_daily_note": "كلمة لنفسك اليوم",
    "get_weather": "Météo",
    "get_calendar": "Agenda du jour",
    "get_deadlines": "Échéances",
    "get_word": "Mot du jour",
    "get_challenge_reminder": "تحدّي اليوم",
    "get_evening_verse": "آية المساء",
    "get_tomorrow_calendar": "Agenda de demain",
    "get_tomorrow_deadlines": "À rendre demain",
    "get_closing_note": "قبل النوم",
}


def morning_sources() -> list[Source]:
    sources: list[Source] = []
    if config.ENABLE_QURAN:
        sources.append(quran.get_verse)
    if config.ENABLE_DAILY_NOTE:
        sources.append(notes.get_daily_note)
    sources += [weather.get_weather, calendar.get_calendar, deadlines.get_deadlines]
    if config.ENABLE_WORD:
        sources.append(word.get_word)
    return sources


def evening_sources() -> list[Source]:
    sources: list[Source] = []
    if config.ENABLE_DAILY_NOTE:
        sources.append(notes.get_challenge_reminder)
    if config.ENABLE_EVENING_VERSE:
        sources.append(quran.get_evening_verse)
    sources += [calendar.get_tomorrow_calendar, deadlines.get_tomorrow_deadlines]
    if config.ENABLE_CLOSING_NOTE:
        sources.append(notes.get_closing_note)  # always the last line
    return sources


def run_sources(greeting: str, sources: list[Source]) -> list[str]:
    """Run every source; a failing one is replaced by a short fallback line
    and logged with its error type only (Actions logs are public)."""
    sections = [greeting]
    for source in sources:
        try:
            section = source()
            if section is not None:
                sections.append(section)
        except Exception as exc:
            status = getattr(getattr(exc, "response", None), "status_code", "")
            print(f"[warn] {source.__name__} failed: {type(exc).__name__} {status}",
                  file=sys.stderr)
            label = SOURCE_LABELS.get(source.__name__, source.__name__)
            sections.append(f"⚠️ <b>{label}</b> indisponible aujourd'hui.")
    return sections


def build_sections(evening: bool = False) -> list[str]:
    day = utils.format_long_date(utils.today())
    if evening:
        return run_sources(f"🌙 <b>Bonsoir</b> {day}", evening_sources())
    return run_sources(f"🌅 <b>Bonjour !</b> {day}", morning_sources())


def build_weekly_sections() -> list[str]:
    return weekly.build_weekly_sections()


def redact(section: str) -> str:
    """Hide private content for public CI logs; keep only headers."""
    # Private text on the header line itself: keep the prefix only.
    for prefix in (notes.CHALLENGE_HEADER, notes.CLOSING_NOTE_HEADER):
        if section.startswith(prefix):
            return f"{prefix} [hidden in CI logs]"
    # Header line is not private (title or date): keep it, hide the rest.
    for prefix in (
        notes.DAILY_NOTE_HEADER,
        word.WORD_HEADER,
        calendar.CALENDAR_PREFIX,  # every 📆 calendar section
        deadlines.DEADLINES_HEADER_PREFIX,
        deadlines.TOMORROW_DEADLINES_HEADER,
        weekly.WEEKLY_DEADLINES_HEADER,
    ):
        if section.startswith(prefix):
            return f"{section.splitlines()[0]}\n[hidden in CI logs]"
    return section
