"""Verse of the day (morning) and evening verse, from api.alquran.cloud.

Text and tafsir are shown exactly as returned by the API."""

from typing import Any

from brief import config, utils
from brief.http import get_json

QURAN_API = "https://api.alquran.cloud/v1/ayah/{ref}/editions/quran-uthmani,ar.muyassar"
TOTAL_AYAHS = 6236
MAX_LENGTH = 400  # morning: skip longer ayahs and take the next one
MAX_SKIPS = 30

VERSE_HEADER = "📖 <b>آية اليوم</b>"
EVENING_VERSE_HEADER = "📖 <b>آية المساء</b>"


def fetch_ayah(ref: int | str, label: str = "get_verse") -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (arabic, tafsir) entries for a global ayah number (e.g. 262)
    or a "surah:ayah" reference (e.g. "2:255")."""
    data = get_json(QURAN_API.format(ref=ref), label=label)["data"]
    by_edition = {entry["edition"]["identifier"]: entry for entry in data}
    return by_edition["quran-uthmani"], by_edition["ar.muyassar"]


def render_ayah(header: str, ayah: dict[str, Any], tafsir: dict[str, Any]) -> str:
    return "\n".join([
        header,
        f"﴿ {utils.escape(ayah['text'])} ﴾",
        f"{utils.escape(ayah['surah']['name'])} — الآية {ayah['numberInSurah']}",
        f"<b>التفسير:</b> {utils.escape(tafsir['text'])}",
    ])


def daily_ayah_number(day_ordinal: int) -> int:
    """Global ayah number (1..6236) for a date, cycling through all ayahs."""
    return day_ordinal % TOTAL_AYAHS + 1


def get_verse() -> str:
    number = daily_ayah_number(utils.today().toordinal())
    for _ in range(MAX_SKIPS):
        ayah, tafsir = fetch_ayah(number)
        if len(ayah["text"]) <= MAX_LENGTH:
            return render_ayah(VERSE_HEADER, ayah, tafsir)
        number = number % TOTAL_AYAHS + 1
    raise RuntimeError("no short enough ayah found")


def get_evening_verse() -> str | None:
    """Verse picked by date from a list of "surah:ayah" references
    (EVENING_VERSES_JSON or a local file). Skipped when not configured."""
    refs = utils.load_json(config.EVENING_VERSES_JSON, config.EVENING_VERSES_FILE)
    if not refs:
        return None
    ref = utils.pick_by_date(refs, utils.today())
    ayah, tafsir = fetch_ayah(ref, label="get_evening_verse")
    return render_ayah(EVENING_VERSE_HEADER, ayah, tafsir)
