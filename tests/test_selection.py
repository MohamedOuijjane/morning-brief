"""Daily picks are deterministic: same content all day, cycling over time."""

import json
from datetime import date
from typing import Any

from brief import config, personal, quran, utils, word

TODAY = date(2026, 11, 16)  # frozen in conftest


def ayah(text: str, number: int = 1) -> dict[str, Any]:
    return {"text": text, "numberInSurah": number, "surah": {"name": "سورة الاختبار"}}


def test_ayah_number_is_stable_and_in_range() -> None:
    n = quran.daily_ayah_number(TODAY.toordinal())
    assert 1 <= n <= quran.TOTAL_AYAHS
    assert quran.daily_ayah_number(TODAY.toordinal() + quran.TOTAL_AYAHS) == n
    assert quran.daily_ayah_number(TODAY.toordinal() + 1) == n % quran.TOTAL_AYAHS + 1


def test_verse_skips_long_ayahs(monkeypatch) -> None:
    requested: list[int | str] = []

    def fake_fetch(ref: int | str, label: str = "") -> tuple[dict, dict]:
        requested.append(ref)
        text = "ا" * 500 if len(requested) == 1 else "نص قصير"
        return ayah(text, 7), {"text": "تفسير"}

    monkeypatch.setattr(quran, "fetch_ayah", fake_fetch)
    first = quran.daily_ayah_number(TODAY.toordinal())
    text = quran.get_verse()
    assert requested == [first, first % quran.TOTAL_AYAHS + 1]
    assert "﴿ نص قصير ﴾" in text and "الآية 7" in text


def test_verse_and_tafsir_are_shown_unchanged(monkeypatch) -> None:
    long_tafsir = "تفسير " * 120  # never cut, even when long
    monkeypatch.setattr(
        quran, "fetch_ayah", lambda ref, label="": (ayah("آية"), {"text": long_tafsir})
    )
    text = quran.get_verse()
    assert text.splitlines() == [
        "📖 <b>آية اليوم</b>",
        "﴿ آية ﴾",
        "سورة الاختبار — الآية 1",
        f"<b>التفسير:</b> {long_tafsir}",
    ]


def test_evening_verse_reference_picked_by_date(monkeypatch) -> None:
    refs = json.loads(utils.resolve(config.EVENING_VERSES_FILE).read_text())
    seen: list[int | str] = []
    monkeypatch.setattr(
        quran, "fetch_ayah", lambda ref, label="": (seen.append(ref) or ayah("آية"), {"text": "ت"})
    )
    text = quran.get_evening_verse()
    assert seen == [refs[TODAY.toordinal() % len(refs)]]
    assert text.startswith("📖 <b>آية المساء</b>")


def test_evening_verse_references_are_well_formed() -> None:
    refs = json.loads(utils.resolve(config.EVENING_VERSES_FILE).read_text())
    assert refs and len(refs) == len(set(refs))
    for ref in refs:
        surah, number = ref.split(":")
        assert 1 <= int(surah) <= 114 and int(number) >= 1


def test_self_talk_and_evening_challenge_match() -> None:
    examples = json.loads(utils.resolve("self_talk.example.json").read_text())
    expected = examples[TODAY.toordinal() % len(examples)]
    assert f"« {expected['title']} »" in personal.get_self_talk()
    reminder = personal.get_challenge_reminder()
    assert reminder == f"{personal.CHALLENGE_HEADER} {expected['challenge']}\nهل فعلته؟"


def test_self_talk_changes_the_next_day(freeze) -> None:
    today_text = personal.get_self_talk()
    freeze("2026-11-17T08:00:00")
    assert personal.get_self_talk() != today_text


def test_night_note_from_secret(monkeypatch) -> None:
    notes = ["ملاحظة أولى", "ملاحظة ثانية", "ملاحظة ثالثة"]
    monkeypatch.setattr(config, "NIGHT_NOTES_JSON", json.dumps(notes))
    assert personal.get_night_note() == (
        f"{personal.NIGHT_NOTE_HEADER} {notes[TODAY.toordinal() % 3]}"
    )


def test_word_picked_by_day_of_year() -> None:
    words = json.loads(utils.resolve("words.example.json").read_text())
    expected = words[TODAY.timetuple().tm_yday % len(words)]
    lines = word.get_word().splitlines()
    assert lines[0] == "💬 <b>Mot du jour</b>"
    assert lines[1] == f"🇸🇦 <b>{expected['ar']}</b> — {expected['ar_example']}"
    assert lines[2].startswith(f"🇫🇷 <b>{expected['fr']}</b>")
    assert lines[3].startswith(f"🇬🇧 <b>{expected['en']}</b>")
