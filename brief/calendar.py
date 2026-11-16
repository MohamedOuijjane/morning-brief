"""Agenda sections from one or more secret iCal feeds.

Each calendar is fetched independently. A failing calendar is logged with
its index and exception type only, never its URL or event titles."""

import sys
from datetime import date, datetime, timedelta
from datetime import time as dt_time
from zoneinfo import ZoneInfo

import icalendar
import recurring_ical_events

from brief import config, utils
from brief.http import http_get

CALENDAR_HEADER = "📆 <b>Agenda du jour</b>"
TOMORROW_CALENDAR_HEADER = "📆 <b>Demain</b>"
CALENDAR_PREFIX = "📆 <b>"  # every calendar section starts with this

ALL_DAY = "Toute la journée"
ONGOING = "En cours"

# (sort key, time label, title)
Event = tuple[tuple[int, str], str, str]


def calendar_urls() -> list[str]:
    """Secret iCal URLs: one per line in GCAL_ICS_URLS, plus GCAL_ICS_URL.
    Blank lines, lines starting with # and duplicates are ignored."""
    urls: list[str] = []
    for line in config.GCAL_ICS_URLS.splitlines() + [config.GCAL_ICS_URL]:
        line = line.strip()
        if line and not line.startswith("#"):
            if line.startswith("webcal://"):
                line = "https://" + line[len("webcal://"):]
            if line not in urls:
                urls.append(line)
    return urls


def fetch_calendars() -> tuple[list[icalendar.Calendar], int]:
    """Download and parse every configured calendar once.
    Returns (calendars, number_failed)."""
    calendars: list[icalendar.Calendar] = []
    failed = 0
    for n, url in enumerate(calendar_urls(), 1):
        label = f"calendar {n}"
        try:
            calendars.append(icalendar.Calendar.from_ical(http_get(url, label=label).content))
        except Exception as exc:
            print(f"[warn] {label} failed: {type(exc).__name__}", file=sys.stderr)
            failed += 1
    return calendars, failed


def events_on(cal: icalendar.Calendar, day: date, tz: ZoneInfo) -> list[Event]:
    """Every event occurring on `day` in `tz`, recurring events expanded."""
    start = datetime.combine(day, dt_time.min, tz)
    events: list[Event] = []
    for event in recurring_ical_events.of(cal).between(start, start + timedelta(days=1)):
        title = str(event.get("SUMMARY", "")).strip() or "(sans titre)"
        begin = event.get("DTSTART").dt
        if isinstance(begin, datetime):
            if begin.tzinfo is None:  # floating time: treat as local time
                begin = begin.replace(tzinfo=tz)
            begin = begin.astimezone(tz)
            if begin.date() < day:  # started before that day, still running
                events.append(((1, "00:00"), ONGOING, title))
            else:
                hhmm = begin.strftime("%H:%M")
                events.append(((1, hhmm), hhmm, title))
        else:  # date only: all-day event
            events.append(((0, ""), ALL_DAY, title))
    return events


def merged_events(
    calendars: list[icalendar.Calendar], day: date, tz: ZoneInfo
) -> list[tuple[str, str]]:
    """Events of all calendars on `day`: all-day first, then by time, with
    duplicates (same title and start) removed. Returns (time_label, title)."""
    seen: set[tuple[str, str]] = set()
    merged: list[tuple[tuple[int, str], str, str, str]] = []
    for cal in calendars:
        for key, when, title in events_on(cal, day, tz):
            if (title, when) not in seen:
                seen.add((title, when))
                merged.append((key, title.casefold(), when, title))
    merged.sort()
    return [(when, title) for _, _, when, title in merged]


def agenda(day: date, header: str, empty_text: str) -> str | None:
    if not calendar_urls():
        return None  # not configured: skip the section silently
    calendars, failed = fetch_calendars()
    if not calendars:
        raise RuntimeError("all calendars failed")
    events = merged_events(calendars, day, ZoneInfo(config.TIMEZONE))
    lines = [header]
    if not events:
        lines.append(empty_text)
    lines += [f"{when}  {utils.escape(title)}" for when, title in events]
    if failed:
        lines.append(f"⚠️ {failed} agenda(s) indisponible(s).")
    return "\n".join(lines)


def get_calendar() -> str | None:
    return agenda(utils.today(), CALENDAR_HEADER, "Aucun événement aujourd'hui.")


def get_tomorrow_calendar() -> str | None:
    tomorrow = utils.today() + timedelta(days=1)
    return agenda(tomorrow, TOMORROW_CALENDAR_HEADER, "Aucun événement demain.")
