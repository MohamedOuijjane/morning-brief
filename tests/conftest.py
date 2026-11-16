"""Shared fixtures: no network, no local data files, a frozen clock.

All test data is neutral and defined here or inline in the tests."""

import os

os.environ["BRIEF_NO_DOTENV"] = "1"  # never load a local .env in tests

import json  # noqa: E402
from collections.abc import Callable, Iterator  # noqa: E402
from datetime import datetime  # noqa: E402
from typing import Any  # noqa: E402
from zoneinfo import ZoneInfo  # noqa: E402

import pytest  # noqa: E402
import requests  # noqa: E402

from brief import config, http, utils  # noqa: E402

SAMPLE_DEADLINES = [
    {"title": "Past item", "date": "2026-11-15"},
    {"title": "Item <today>", "date": "2026-11-16"},
    {"title": "Item tomorrow", "date": "2026-11-17"},
    {"title": "Item in 4 days", "date": "2026-11-20"},
    {"title": "Item next week", "date": "2026-11-26"},
    {"title": "Item in 14 days", "date": "2026-11-30"},
    {"title": "Item too far", "date": "2026-12-01"},
]

SAMPLE_DAILY_NOTES = [
    {"title": f"Sample title {i}", "body": f"Sample text {i}", "challenge": f"Sample task {i}"}
    for i in range(3)
]

SAMPLE_CLOSING_NOTES = ["Sample note 0", "Sample note 1", "Sample note 2"]

SAMPLE_WORDS = [
    {"ar": f"ar-{i}", "fr": f"fr-{i}", "en": f"en-{i}",
     "ar_example": f"ar example {i}", "fr_example": f"fr example {i}",
     "en_example": f"en example {i}"}
    for i in range(5)
]

# Two calendars. Today is Monday 16 November 2026 (Europe/Paris).
CALENDAR_A = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//A//EN
BEGIN:VEVENT
UID:a1@test.invalid
SUMMARY:Weekly event
DTSTART;TZID=Europe/Paris:20261005T090000
DTEND;TZID=Europe/Paris:20261005T100000
RRULE:FREQ=WEEKLY;BYDAY=MO
END:VEVENT
BEGIN:VEVENT
UID:a2@test.invalid
SUMMARY:All-day event
DTSTART;VALUE=DATE:20261116
DTEND;VALUE=DATE:20261117
END:VEVENT
BEGIN:VEVENT
UID:a3@test.invalid
SUMMARY:UTC event
DTSTART:20261116T130000Z
DTEND:20261116T140000Z
END:VEVENT
BEGIN:VEVENT
UID:a4@test.invalid
SUMMARY:Tomorrow event
DTSTART;TZID=Europe/Paris:20261117T100000
DTEND;TZID=Europe/Paris:20261117T110000
END:VEVENT
END:VCALENDAR
"""

CALENDAR_B = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//B//EN
BEGIN:VEVENT
UID:b1@test.invalid
SUMMARY:Weekly event
DTSTART;TZID=Europe/Paris:20261116T090000
DTEND;TZID=Europe/Paris:20261116T100000
END:VEVENT
BEGIN:VEVENT
UID:b2@test.invalid
SUMMARY:Multi-day event
DTSTART;VALUE=DATE:20261115
DTEND;VALUE=DATE:20261118
END:VEVENT
BEGIN:VEVENT
UID:b3@test.invalid
SUMMARY:Daily event
DTSTART;TZID=Europe/Paris:20261101T183000
DTEND;TZID=Europe/Paris:20261101T193000
RRULE:FREQ=DAILY
EXDATE;TZID=Europe/Paris:20261115T183000
END:VEVENT
BEGIN:VEVENT
UID:b4@test.invalid
SUMMARY:Overnight event
DTSTART;TZID=Europe/Paris:20261115T230000
DTEND;TZID=Europe/Paris:20261116T010000
END:VEVENT
BEGIN:VEVENT
UID:b5@test.invalid
SUMMARY:Tuesday event
DTSTART;TZID=Europe/Paris:20261110T070000
RRULE:FREQ=WEEKLY;BYDAY=TU
END:VEVENT
END:VCALENDAR
"""


@pytest.fixture(autouse=True)
def isolated(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Iterator[None]:
    """Block real HTTP; use only the sample data above. Local data files are
    pointed at an empty temporary folder, so real files are never read."""

    def blocked(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("network access is blocked in tests")

    monkeypatch.setattr(requests.sessions.Session, "request", blocked)
    monkeypatch.setattr(http, "HTTP_BACKOFF", 0)

    settings: dict[str, Any] = {
        "TIMEZONE": "Europe/Paris",
        "CITY_NAME": "Sample City",
        "TELEGRAM_TOKEN": "",
        "TELEGRAM_CHAT_ID": "",
        "DEADLINES_DAYS": 14,
        "DEADLINES_JSON": json.dumps(SAMPLE_DEADLINES),
        "DAILY_NOTE_JSON": json.dumps(SAMPLE_DAILY_NOTES),
        "CLOSING_NOTE_JSON": json.dumps(SAMPLE_CLOSING_NOTES),
        "WORDS_JSON": json.dumps(SAMPLE_WORDS),
        "EVENING_VERSES_JSON": json.dumps(["1:1", "2:2", "3:3"]),
        "GCAL_ICS_URLS": "",
        "GCAL_ICS_URL": "",
        "IN_CI": False,
        "DRY_RUN": False,
    }
    for name in ("DEADLINES", "DAILY_NOTE", "CLOSING_NOTE", "WORDS", "EVENING_VERSES"):
        settings[f"{name}_FILE"] = str(tmp_path / f"missing_{name.lower()}.json")
    for flag in ("QURAN", "DAILY_NOTE", "WORD", "EVENING", "EVENING_VERSE",
                 "CLOSING_NOTE", "WEEKLY"):
        settings[f"ENABLE_{flag}"] = True
    for name, value in settings.items():
        monkeypatch.setattr(config, name, value)
    yield


@pytest.fixture(autouse=True)
def freeze(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], None]:
    """Freeze the clock. Default: Monday 16 November 2026, 08:00 in Paris.
    Call freeze("2026-11-16T23:30:00+00:00") to move it."""

    def _freeze(iso: str) -> None:
        moment = datetime.fromisoformat(iso)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=ZoneInfo("Europe/Paris"))
        monkeypatch.setattr(utils, "now", lambda: moment.astimezone(ZoneInfo(config.TIMEZONE)))

    _freeze("2026-11-16T08:00:00")
    return _freeze


class FakeResponse:
    def __init__(self, status: int = 200, content: bytes = b"", data: Any = None) -> None:
        self.status_code = status
        self.content = content
        self._data = data
        self.ok = status < 400
        self.text = content.decode("utf-8", "replace")

    def json(self) -> Any:
        return self._data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)  # type: ignore[arg-type]


@pytest.fixture
def fake_get(monkeypatch: pytest.MonkeyPatch) -> Callable[[dict[str, Any]], list[str]]:
    """Route requests.get by URL. Each route value is a FakeResponse, an
    exception instance, or a list of those (consumed in order).
    Returns the list of requested URLs."""

    def install(routes: dict[str, Any]) -> list[str]:
        calls: list[str] = []

        def get(url: str, params: Any = None, timeout: float | None = None) -> FakeResponse:
            calls.append(url)
            if url not in routes:
                raise requests.ConnectionError("no route")
            outcome = routes[url]
            if isinstance(outcome, list):
                outcome = outcome.pop(0) if len(outcome) > 1 else outcome[0]
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        monkeypatch.setattr(requests, "get", get)
        return calls

    return install


def ics_response(text: str) -> FakeResponse:
    return FakeResponse(content=text.encode())
