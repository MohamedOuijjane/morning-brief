"""Calendar merging, dedup, recurrence and timezones with inline .ics data.

Today is Monday 16 November 2026 in Europe/Paris (see conftest)."""

import pytest

from brief import calendar, config, messages
from tests.conftest import CALENDAR_A, CALENDAR_B, FakeResponse, ics_response

URL_A = "https://calendar.test.invalid/a.ics"
URL_B = "https://calendar.test.invalid/b.ics"
URL_BAD = "https://calendar.test.invalid/missing.ics"


@pytest.fixture
def two_calendars(monkeypatch, fake_get):
    monkeypatch.setattr(config, "GCAL_ICS_URLS", f"{URL_A}\n{URL_B}")
    return fake_get({URL_A: ics_response(CALENDAR_A), URL_B: ics_response(CALENDAR_B)})


def test_today_merged_sorted_and_deduplicated(two_calendars) -> None:
    assert calendar.get_calendar().splitlines() == [
        "📆 <b>Agenda du jour</b>",
        "Toute la journée  All-day event",
        "Toute la journée  Multi-day event",
        "En cours  Overnight event",  # 23:00 yesterday -> 01:00 today
        "09:00  Weekly event",  # in both calendars, shown once
        "14:00  UTC event",  # 13:00 UTC -> 14:00 Paris
        "18:30  Daily event",
    ]


def test_each_calendar_is_fetched_once(two_calendars) -> None:
    calendar.get_calendar()
    assert two_calendars == [URL_A, URL_B]


def test_tomorrow_uses_recurrences_and_skips_today_only_events(two_calendars) -> None:
    lines = calendar.get_tomorrow_calendar().splitlines()
    assert lines[0] == "📆 <b>Demain</b>"
    assert "07:00  Tuesday event" in lines
    assert "10:00  Tomorrow event" in lines
    assert not any("UTC event" in line or "Weekly event" in line for line in lines)


def test_exdate_removes_one_occurrence(two_calendars, freeze) -> None:
    freeze("2026-11-15T08:00:00")
    assert "Daily event" not in calendar.get_calendar()


def test_timezone_conversion(two_calendars, monkeypatch) -> None:
    monkeypatch.setattr(config, "TIMEZONE", "Europe/London")
    assert "13:00  UTC event" in calendar.get_calendar()


def test_empty_day(monkeypatch, fake_get, freeze) -> None:
    monkeypatch.setattr(config, "GCAL_ICS_URL", URL_A)
    fake_get({URL_A: ics_response(CALENDAR_A)})
    freeze("2026-11-18T08:00:00")
    assert calendar.get_calendar() == "📆 <b>Agenda du jour</b>\nAucun événement aujourd'hui."


def test_not_configured_is_skipped() -> None:
    assert calendar.get_calendar() is None
    assert calendar.get_tomorrow_calendar() is None


def test_one_failing_calendar_keeps_the_others(monkeypatch, fake_get, capsys) -> None:
    monkeypatch.setattr(config, "GCAL_ICS_URLS", f"{URL_A}\n{URL_BAD}")
    fake_get({URL_A: ics_response(CALENDAR_A), URL_BAD: FakeResponse(404)})
    text = calendar.get_calendar()
    assert "UTC event" in text
    assert text.endswith("⚠️ 1 agenda(s) indisponible(s).")
    log = capsys.readouterr().err
    assert "calendar 2 failed: HTTPError" in log
    assert "test.invalid" not in log  # never log URLs


def test_all_calendars_failing_is_isolated(monkeypatch, fake_get, capsys) -> None:
    monkeypatch.setattr(config, "GCAL_ICS_URLS", URL_BAD)
    fake_get({URL_BAD: FakeResponse(404)})
    sections = messages.run_sources("greeting", [calendar.get_calendar])
    assert sections == ["greeting", "⚠️ <b>Agenda du jour</b> indisponible aujourd'hui."]
    assert "test.invalid" not in capsys.readouterr().err


def test_url_list_parsing(monkeypatch) -> None:
    monkeypatch.setattr(config, "GCAL_ICS_URLS", f"# comment\n\n{URL_A}\nwebcal://x.invalid/c.ics\n")
    monkeypatch.setattr(config, "GCAL_ICS_URL", URL_A)  # duplicate
    assert calendar.calendar_urls() == [URL_A, "https://x.invalid/c.ics"]
