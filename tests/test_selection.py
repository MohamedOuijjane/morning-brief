"""Daily picks are deterministic: same content all day, cycling over time."""

from datetime import date
from typing import Any

from brief import config, notes, quran, word
from tests.conftest import SAMPLE_CLOSING_NOTES, SAMPLE_DAILY_NOTES, SAMPLE_WORDS

TODAY = date(2026, 11, 16)  # frozen in conftest


def ayah(text: str, number: int = 1) -> dict[str, Any]:
    return {"text": text, "numberInSurah": number, "surah": {"name": "Sample name"}}


def test_ayah_number_is_stable_and_in_range() -> None:
    n = quran.daily_ayah_number(TODAY.toordinal())
    assert 1 <= n <= quran.TOTAL_AYAHS
    assert quran.daily_ayah_number(TODAY.toordinal() + quran.TOTAL_AYAHS) == n
    assert quran.daily_ayah_number(TODAY.toordinal() + 1) == n % quran.TOTAL_AYAHS + 1


def test_verse_skips_long_ayahs(monkeypatch) -> None:
    requested: list[int | str] = []

    def fake_fetch(ref: int | str, label: str = "") -> tuple[dict, dict]:
        requested.append(ref)
        text = "x" * 500 if len(requested) == 1 else "Sample text"
        return ayah(text, 7), {"text": "Sample commentary"}

    monkeypatch.setattr(quran, "fetch_ayah", fake_fetch)
    first = quran.daily_ayah_number(TODAY.toordinal())
    text = quran.get_verse()
    assert requested == [first, first % quran.TOTAL_AYAHS + 1]
    assert "﴿ Sample text ﴾" in text


def test_verse_text_is_shown_unchanged(monkeypatch) -> None:
    long_text = "Sample commentary " * 60  # never cut, even when long
    monkeypatch.setattr(
        quran, "fetch_ayah", lambda ref, label="": (ayah("Sample text"), {"text": long_text})
    )
    lines = quran.get_verse().splitlines()
    assert lines[0] == quran.VERSE_HEADER
    assert lines[1] == "﴿ Sample text ﴾"
    assert lines[2].startswith("Sample name — ")
    assert lines[3].endswith(long_text)


def test_evening_verse_reference_picked_by_date(monkeypatch) -> None:
    seen: list[int | str] = []
    monkeypatch.setattr(
        quran, "fetch_ayah", lambda ref, label="": (seen.append(ref) or ayah("t"), {"text": "c"})
    )
    text = quran.get_evening_verse()
    assert seen == [["1:1", "2:2", "3:3"][TODAY.toordinal() % 3]]
    assert text.startswith(quran.EVENING_VERSE_HEADER)


def test_daily_note_and_evening_challenge_match() -> None:
    expected = SAMPLE_DAILY_NOTES[TODAY.toordinal() % len(SAMPLE_DAILY_NOTES)]
    assert f"« {expected['title']} »" in notes.get_daily_note()
    assert notes.get_challenge_reminder().startswith(
        f"{notes.CHALLENGE_HEADER} {expected['challenge']}\n"
    )


def test_daily_note_changes_the_next_day(freeze) -> None:
    today_text = notes.get_daily_note()
    freeze("2026-11-17T08:00:00")
    assert notes.get_daily_note() != today_text


def test_closing_note_picked_by_date() -> None:
    expected = SAMPLE_CLOSING_NOTES[TODAY.toordinal() % len(SAMPLE_CLOSING_NOTES)]
    assert notes.get_closing_note() == f"{notes.CLOSING_NOTE_HEADER} {expected}"


def test_word_picked_by_day_of_year() -> None:
    expected = SAMPLE_WORDS[TODAY.timetuple().tm_yday % len(SAMPLE_WORDS)]
    lines = word.get_word().splitlines()
    assert lines[0] == word.WORD_HEADER
    assert lines[2] == f"🇫🇷 <b>{expected['fr']}</b> — {expected['fr_example']}"


def test_sections_without_data_are_skipped(monkeypatch) -> None:
    for name in ("DAILY_NOTE_JSON", "CLOSING_NOTE_JSON", "WORDS_JSON", "EVENING_VERSES_JSON"):
        monkeypatch.setattr(config, name, "")
    assert notes.get_daily_note() is None
    assert notes.get_challenge_reminder() is None
    assert notes.get_closing_note() is None
    assert word.get_word() is None
    assert quran.get_evening_verse() is None
