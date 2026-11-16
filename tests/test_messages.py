"""Message assembly, error isolation, redaction, splitting and the CLI."""

from datetime import date

import pytest

from brief import (
    calendar,
    cli,
    config,
    deadlines,
    messages,
    notes,
    quran,
    telegram,
    weather,
    weekly,
    word,
)
from tests.conftest import CALENDAR_A, CALENDAR_B, ics_response


def ok() -> str:
    return "ok section"


def skipped() -> None:
    return None


def get_weather() -> str:
    raise ValueError("boom https://secret.test.invalid/token")


def test_failing_source_is_isolated(capsys) -> None:
    sections = messages.run_sources("hello", [ok, get_weather, skipped, ok])
    fallback = "⚠️ <b>Météo</b> indisponible aujourd'hui."
    assert sections == ["hello", "ok section", fallback, "ok section"]
    log = capsys.readouterr().err
    assert "get_weather failed: ValueError" in log
    assert "secret.test.invalid" not in log  # only the error type is logged


@pytest.fixture
def stub_sources(monkeypatch):
    for module, name in [
        (quran, "get_verse"), (notes, "get_daily_note"), (weather, "get_weather"),
        (calendar, "get_calendar"), (deadlines, "get_deadlines"), (word, "get_word"),
        (notes, "get_challenge_reminder"), (quran, "get_evening_verse"),
        (calendar, "get_tomorrow_calendar"), (deadlines, "get_tomorrow_deadlines"),
        (notes, "get_closing_note"),
    ]:
        monkeypatch.setattr(module, name, lambda name=name: name)


def test_morning_order(stub_sources) -> None:
    assert messages.build_sections() == [
        "🌅 <b>Bonjour !</b> lundi 16 novembre 2026",
        "get_verse", "get_daily_note", "get_weather", "get_calendar", "get_deadlines", "get_word",
    ]


def test_evening_order_ends_with_closing_note(stub_sources) -> None:
    assert messages.build_sections(evening=True) == [
        "🌙 <b>Bonsoir</b> lundi 16 novembre 2026",
        "get_challenge_reminder", "get_evening_verse", "get_tomorrow_calendar",
        "get_tomorrow_deadlines", "get_closing_note",
    ]


def test_toggles(stub_sources, monkeypatch) -> None:
    for flag in ("ENABLE_QURAN", "ENABLE_DAILY_NOTE", "ENABLE_WORD",
                 "ENABLE_EVENING_VERSE", "ENABLE_CLOSING_NOTE"):
        monkeypatch.setattr(config, flag, False)
    assert messages.build_sections()[1:] == ["get_weather", "get_calendar", "get_deadlines"]
    assert messages.build_sections(evening=True)[1:] == [
        "get_tomorrow_calendar", "get_tomorrow_deadlines",
    ]


def test_sections_without_data_are_left_out(monkeypatch) -> None:
    for name in ("DAILY_NOTE_JSON", "CLOSING_NOTE_JSON", "WORDS_JSON",
                 "EVENING_VERSES_JSON", "DEADLINES_JSON"):
        monkeypatch.setattr(config, name, "")
    monkeypatch.setattr(quran, "get_verse", lambda: "verse")
    monkeypatch.setattr(weather, "get_weather", lambda: "weather")
    assert messages.build_sections()[1:] == ["verse", "weather"]
    assert messages.build_sections(evening=True) == ["🌙 <b>Bonsoir</b> lundi 16 novembre 2026"]


def test_redaction_hides_private_content_only() -> None:
    assert messages.redact(notes.get_daily_note()) == (
        f"{notes.DAILY_NOTE_HEADER}\n[hidden in CI logs]"
    )
    assert messages.redact(notes.get_challenge_reminder()) == (
        f"{notes.CHALLENGE_HEADER} [hidden in CI logs]"
    )
    assert messages.redact(notes.get_closing_note()) == (
        f"{notes.CLOSING_NOTE_HEADER} [hidden in CI logs]"
    )
    assert messages.redact(deadlines.get_deadlines()).endswith("[hidden in CI logs]")
    assert messages.redact(word.get_word()).endswith("[hidden in CI logs]")
    assert messages.redact("🌧 <b>Météo</b>\nPluie") == "🌧 <b>Météo</b>\nPluie"


# --- Telegram splitting -------------------------------------------------------

def test_short_message_is_not_split() -> None:
    assert telegram.split_messages(["a", "b"]) == ["a\n\nb"]


def test_split_at_section_boundaries() -> None:
    sections = ["A" * 3000, "B" * 2000, "C" * 500]
    assert telegram.split_messages(sections) == ["A" * 3000, "B" * 2000 + "\n\n" + "C" * 500]


def test_exactly_at_the_limit_stays_whole() -> None:
    sections = ["A" * 2000, "B" * (telegram.TELEGRAM_LIMIT - 2002)]
    parts = telegram.split_messages(sections)
    assert len(parts) == 1 and len(parts[0]) == telegram.TELEGRAM_LIMIT


def test_oversized_section_is_cut_as_last_resort() -> None:
    parts = telegram.split_messages(["x", "Y" * 9000])
    assert parts[0] == "x"
    assert all(len(p) <= telegram.TELEGRAM_LIMIT for p in parts)
    assert "".join(parts[1:]) == "Y" * 9000


# --- Weekly summary -------------------------------------------------------------

URL = "https://calendar.test.invalid/a.ics"


def test_weekly_summary(monkeypatch, fake_get) -> None:
    monkeypatch.setattr(config, "GCAL_ICS_URL", URL)
    fake_get({URL: ics_response(CALENDAR_B)})
    sections = weekly.build_weekly_sections()
    assert sections[0] == "🗓 <b>Semaine du lundi 23 novembre au dimanche 29 novembre</b>"
    assert sections[1] == "📆 <b>Lundi 23</b>\n18:30  Daily event"
    assert sections[2] == "📆 <b>Mardi 24</b>\n07:00  Tuesday event\n18:30  Daily event"
    assert sections[-2] == "⏰ <b>Échéances de la semaine</b>\n• jeu. 26 nov. : Item next week"
    assert sections[-1] == "8 événements, 1 échéance."


def test_weekly_skips_empty_days(monkeypatch, fake_get) -> None:
    monkeypatch.setattr(config, "GCAL_ICS_URL", URL)
    fake_get({URL: ics_response(CALENDAR_A)})  # only the Monday weekly event
    days = [s for s in weekly.build_weekly_sections() if s.startswith("📆")]
    assert days == ["📆 <b>Lundi 23</b>\n09:00  Weekly event"]


def test_free_week(monkeypatch) -> None:
    monkeypatch.setattr(config, "DEADLINES_JSON", "[]")
    assert weekly.build_weekly_sections()[1:] == ["Semaine libre. 🎉"]


def test_failed_calendar_never_claims_a_free_week(monkeypatch, fake_get) -> None:
    monkeypatch.setattr(config, "GCAL_ICS_URL", URL)
    monkeypatch.setattr(config, "DEADLINES_JSON", "[]")
    fake_get({})  # every request fails
    assert weekly.build_weekly_sections()[1:] == [
        "⚠️ <b>Agenda</b> indisponible.", "0 événement, 0 échéance.",
    ]


def test_coming_week_from_sunday() -> None:
    assert weekly.coming_week(date(2026, 11, 22)) == (date(2026, 11, 23), date(2026, 11, 29))


# --- CLI ---------------------------------------------------------------------------

def test_cli_dry_run_prints(stub_sources, capsys) -> None:
    cli.main(["--evening", "--dry-run"])
    out = capsys.readouterr().out
    assert out.startswith("🌙 <b>Bonsoir</b>") and "get_closing_note" in out


def test_cli_dry_run_in_ci_hides_private_sections(monkeypatch, capsys) -> None:
    monkeypatch.setattr(config, "IN_CI", True)
    monkeypatch.setattr(quran, "get_verse", lambda: "verse")
    monkeypatch.setattr(weather, "get_weather", lambda: "weather")
    cli.main(["--dry-run"])
    out = capsys.readouterr().out
    assert out.count("[hidden in CI logs]") == 3  # daily note, deadlines, word
    for private in ("Sample title", "Item in 4 days", "fr-"):
        assert private not in out


def test_cli_sends_every_part(stub_sources, monkeypatch, capsys) -> None:
    sent: list[str] = []
    monkeypatch.setattr(telegram, "send", sent.append)
    cli.main(["--weekly"])
    assert sent and capsys.readouterr().out.strip() == "Weekly summary sent."


def test_cli_disabled_modes(monkeypatch, capsys) -> None:
    monkeypatch.setattr(config, "ENABLE_EVENING", False)
    monkeypatch.setattr(config, "ENABLE_WEEKLY", False)
    cli.main(["--evening"])
    cli.main(["--weekly"])
    assert "disabled" in capsys.readouterr().out
