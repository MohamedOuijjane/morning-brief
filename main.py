"""Morning brief and evening message, sent to Telegram.

    python main.py             # morning: verse, self-talk, weather, agenda,
                               # deadlines, word of the day
    python main.py --evening   # evening: challenge reminder, verse, tomorrow's
                               # agenda and deadlines, bedtime note
    python main.py --weekly    # Sunday: events and deadlines of the coming week

The message itself is in French; dates are formatted with hardcoded name
lists so the output does not depend on the system locale.
"""

import argparse
import json
import sys
import time
from datetime import date, datetime, timedelta
from datetime import time as dt_time
from pathlib import Path
from zoneinfo import ZoneInfo

import icalendar
import recurring_ical_events
import requests

import config

BASE_DIR = Path(__file__).parent

HTTP_ATTEMPTS = 3
HTTP_TIMEOUT = 20  # seconds per attempt
HTTP_BACKOFF = 2  # seconds, doubled after each failed attempt

TELEGRAM_LIMIT = 4096  # max characters per Telegram message

QURAN_API = "https://api.alquran.cloud/v1/ayah/{number}/editions/quran-uthmani,ar.muyassar"
QURAN_TOTAL_AYAHS = 6236
QURAN_MAX_LENGTH = 400  # skip longer ayahs and take the next one
QURAN_MAX_SKIPS = 30

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

# WMO weather interpretation codes used by Open-Meteo.
WEATHER_CODES = {
    0: ("Ciel dégagé", "☀️"),
    1: ("Plutôt dégagé", "🌤"),
    2: ("Partiellement nuageux", "⛅"),
    3: ("Couvert", "☁️"),
    45: ("Brouillard", "🌫"),
    48: ("Brouillard givrant", "🌫"),
    51: ("Bruine légère", "🌦"),
    53: ("Bruine", "🌦"),
    55: ("Bruine dense", "🌦"),
    56: ("Bruine verglaçante légère", "🌧"),
    57: ("Bruine verglaçante dense", "🌧"),
    61: ("Pluie faible", "🌧"),
    63: ("Pluie", "🌧"),
    65: ("Forte pluie", "🌧"),
    66: ("Pluie verglaçante légère", "🌧"),
    67: ("Forte pluie verglaçante", "🌧"),
    71: ("Neige faible", "🌨"),
    73: ("Neige", "🌨"),
    75: ("Forte neige", "❄️"),
    77: ("Grains de neige", "🌨"),
    80: ("Averses légères", "🌦"),
    81: ("Averses", "🌧"),
    82: ("Averses violentes", "⛈"),
    85: ("Averses de neige", "🌨"),
    86: ("Fortes averses de neige", "❄️"),
    95: ("Orage", "⛈"),
    96: ("Orage avec grêle", "⛈"),
    99: ("Orage avec forte grêle", "⛈"),
}

# Section names used in the fallback line when a source fails.
SOURCE_LABELS = {
    "get_verse": "Verset du jour",
    "get_self_talk": "كلمة لنفسك اليوم",
    "get_weather": "Météo",
    "get_calendar": "Agenda du jour",
    "get_deadlines": "Échéances",
    "get_word": "Mot du jour",
    "get_challenge_reminder": "تحدّي اليوم",
    "get_evening_verse": "آية المساء",
    "get_tomorrow_calendar": "Agenda de demain",
    "get_tomorrow_deadlines": "À rendre demain",
    "get_night_note": "قبل النوم",
}


def today() -> date:
    return datetime.now(ZoneInfo(config.TIMEZONE)).date()


def format_long_date(d: date) -> str:
    """e.g. 'lundi 16 novembre 2026'."""
    return f"{DAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]} {d.year}"


def format_short_date(d: date) -> str:
    """e.g. 'mar. 17 nov.'."""
    return f"{DAYS_SHORT[d.weekday()]} {d.day} {MONTHS_SHORT[d.month - 1]}"


def _fr_number(value) -> str:
    """French decimal separator: 10.9 -> '10,9'."""
    return str(value).replace(".", ",")


def _get_json(url: str, params: dict | None = None, label: str = "request") -> dict:
    return _http_get(url, params=params, label=label).json()


def _http_get(url: str, params: dict | None = None, label: str = "request"):
    """GET with retries on timeouts, connection errors, 429 and 5xx.
    Logs only the label and error type, never the URL."""
    delay = HTTP_BACKOFF
    for attempt in range(1, HTTP_ATTEMPTS + 1):
        try:
            resp = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
            if resp.status_code == 429 or resp.status_code >= 500:
                resp.raise_for_status()
            break
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
            if attempt == HTTP_ATTEMPTS:
                raise
            status = getattr(exc.response, "status_code", "")
            print(
                f"[retry] {label} attempt {attempt} failed: "
                f"{type(exc).__name__} {status}, retrying in {delay}s",
                file=sys.stderr,
            )
            time.sleep(delay)
            delay *= 2
    resp.raise_for_status()  # other 4xx (e.g. bad parameters): no retry
    return resp


def _fetch_ayah(ref, label: str = "get_verse") -> tuple[dict, dict]:
    """Return (arabic, tafsir) edition entries for a global ayah number
    (e.g. 262) or a "surah:ayah" reference (e.g. "2:255")."""
    data = _get_json(QURAN_API.format(number=ref), label=label)["data"]
    by_edition = {entry["edition"]["identifier"]: entry for entry in data}
    return by_edition["quran-uthmani"], by_edition["ar.muyassar"]


def _render_ayah(header: str, ayah: dict, tafsir: dict) -> str:
    # Text and tafsir are shown exactly as returned by the API.
    return "\n".join([
        header,
        f"﴿ {_escape(ayah['text'])} ﴾",
        f"{_escape(ayah['surah']['name'])} — الآية {ayah['numberInSurah']}",
        f"<b>التفسير:</b> {_escape(tafsir['text'])}",
    ])


def get_verse() -> str:
    # Same ayah for the whole day, cycling through all ayahs over time.
    number = today().toordinal() % QURAN_TOTAL_AYAHS + 1
    for _ in range(QURAN_MAX_SKIPS):
        ayah, tafsir = _fetch_ayah(number)
        if len(ayah["text"]) <= QURAN_MAX_LENGTH:
            break
        number = number % QURAN_TOTAL_AYAHS + 1
    else:
        raise RuntimeError("no short enough ayah found")
    return _render_ayah("📖 <b>آية اليوم</b>", ayah, tafsir)


def get_evening_verse() -> str:
    # Fixed list of references, picked by date (same verse all evening).
    path = BASE_DIR / config.EVENING_VERSES_FILE
    refs = json.loads(path.read_text(encoding="utf-8"))
    ref = refs[today().toordinal() % len(refs)]
    ayah, tafsir = _fetch_ayah(ref, label="get_evening_verse")
    return _render_ayah("📖 <b>آية المساء</b>", ayah, tafsir)


SELF_TALK_HEADER = "💬 <b>كلمة لنفسك اليوم</b>"


def _load_self_talk() -> list:
    if config.SELF_TALK_JSON:
        return json.loads(config.SELF_TALK_JSON)
    for name in (config.SELF_TALK_FILE, config.SELF_TALK_FALLBACK_FILE):
        path = Path(name)
        if not path.is_absolute():
            path = BASE_DIR / path
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError("no self-talk messages found")


def _todays_self_talk() -> dict:
    # Same date-based pick for the morning message and the evening reminder.
    messages = _load_self_talk()
    return messages[today().toordinal() % len(messages)]


CHALLENGE_HEADER = "🎯 <b>تحدّي اليوم:</b>"


def get_challenge_reminder() -> str:
    # Private content: never print or log it (see main()).
    msg = _todays_self_talk()
    return f"{CHALLENGE_HEADER} {_escape(msg['challenge'])}\nهل فعلته؟"


NIGHT_NOTE_HEADER = "🌃 <b>قبل النوم:</b>"


def _load_night_notes() -> list:
    if config.NIGHT_NOTES_JSON:
        return json.loads(config.NIGHT_NOTES_JSON)
    for name in (config.NIGHT_NOTES_FILE, config.NIGHT_NOTES_FALLBACK_FILE):
        path = Path(name)
        if not path.is_absolute():
            path = BASE_DIR / path
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError("no night notes found")


def get_night_note() -> str:
    # Private content: never print or log it (see main()).
    notes = _load_night_notes()
    return f"{NIGHT_NOTE_HEADER} {_escape(notes[today().toordinal() % len(notes)])}"


def get_self_talk() -> str:
    # Private content: never print or log it (see main()).
    msg = _todays_self_talk()
    return "\n".join([
        SELF_TALK_HEADER,
        f"« {_escape(msg['title'])} »",
        _escape(msg["body"]),
        f"{CHALLENGE_HEADER} {_escape(msg['challenge'])}",
    ])


def get_word() -> str:
    path = Path(config.WORDS_FILE)
    if not path.is_absolute():
        path = BASE_DIR / path
    words = json.loads(path.read_text(encoding="utf-8"))
    word = words[today().timetuple().tm_yday % len(words)]
    return "\n".join([
        "💬 <b>Mot du jour</b>",
        f"🇸🇦 <b>{_escape(word['ar'])}</b> — {_escape(word['ar_example'])}",
        f"🇫🇷 <b>{_escape(word['fr'])}</b> — {_escape(word['fr_example'])}",
        f"🇬🇧 <b>{_escape(word['en'])}</b> — {_escape(word['en_example'])}",
    ])


def _fetch_forecast() -> dict:
    params = {
        "latitude": config.LATITUDE,
        "longitude": config.LONGITUDE,
        "timezone": config.TIMEZONE,
        "current": "temperature_2m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
        "precipitation_probability_max,wind_speed_10m_max",
        "forecast_days": 1,
    }
    return _get_json(
        "https://api.open-meteo.com/v1/forecast", params=params, label="get_weather"
    )


def get_weather() -> str:
    data = _fetch_forecast()
    daily = data["daily"]
    current = data.get("current", {})

    code = daily["weather_code"][0]
    label, icon = WEATHER_CODES.get(code, ("Inconnu", "🌡"))
    lines = [
        f"{icon} <b>Météo à {_escape(config.CITY_NAME)}</b>",
        label,
        f"Actuellement : {_fr_number(current.get('temperature_2m', '?'))} °C",
        f"Min / Max : {_fr_number(daily['temperature_2m_min'][0])} °C"
        f" / {_fr_number(daily['temperature_2m_max'][0])} °C",
        f"Risque de pluie : {daily['precipitation_probability_max'][0]} %",
        f"Vent : jusqu'à {_fr_number(daily['wind_speed_10m_max'][0])} km/h",
    ]
    return "\n".join(lines)


CALENDAR_HEADER = "📆 <b>Agenda du jour</b>"


def _calendar_urls() -> list[str]:
    """Secret iCal URLs: one per line in GCAL_ICS_URLS, plus GCAL_ICS_URL."""
    urls = []
    for line in config.GCAL_ICS_URLS.splitlines() + [config.GCAL_ICS_URL]:
        line = line.strip()
        if line and not line.startswith("#"):
            if line.startswith("webcal://"):
                line = "https://" + line[len("webcal://"):]
            if line not in urls:
                urls.append(line)
    return urls


def _fetch_calendars() -> tuple[list, int]:
    """Download and parse every configured calendar once.
    Returns (calendars, number_failed). A failed calendar is logged with its
    index and exception type only, never its URL or contents."""
    calendars, failed = [], 0
    for n, url in enumerate(_calendar_urls(), 1):
        label = f"calendar {n}"
        try:
            calendars.append(
                icalendar.Calendar.from_ical(_http_get(url, label=label).content)
            )
        except Exception as exc:
            print(f"[warn] {label} failed: {type(exc).__name__}", file=sys.stderr)
            failed += 1
    return calendars, failed


def _merged_events(calendars: list, day: date, tz: ZoneInfo) -> list:
    """Events of all calendars on `day`: sorted (all-day first, then by time),
    duplicates (same title and start) removed. Returns (time_label, title)."""
    events, seen = [], set()
    for cal in calendars:
        for key, when, title in _calendar_events(cal, day, tz):
            if (title, when) not in seen:
                seen.add((title, when))
                events.append((key, title.casefold(), when, title))
    events.sort()
    return [(when, title) for _, _, when, title in events]


def _calendar_events(cal, day: date, tz: ZoneInfo) -> list:
    """Return (sort_key, time_label, title) for every event occurring on `day`."""
    start = datetime.combine(day, dt_time.min, tz)
    end = start + timedelta(days=1)
    events = []
    for event in recurring_ical_events.of(cal).between(start, end):
        title = str(event.get("SUMMARY", "")).strip() or "(sans titre)"
        begin = event.get("DTSTART").dt
        if isinstance(begin, datetime):
            if begin.tzinfo is None:  # floating time: treat as local time
                begin = begin.replace(tzinfo=tz)
            begin = begin.astimezone(tz)
            if begin.date() < day:  # started before that day, still running
                events.append(((1, "00:00"), "En cours", title))
            else:
                hhmm = begin.strftime("%H:%M")
                events.append(((1, hhmm), hhmm, title))
        else:  # date only: all-day event
            events.append(((0, ""), "Toute la journée", title))
    return events


def get_calendar() -> str | None:
    return _agenda(today(), CALENDAR_HEADER, "Aucun événement aujourd'hui.")


TOMORROW_CALENDAR_HEADER = "📆 <b>Demain</b>"


def get_tomorrow_calendar() -> str | None:
    return _agenda(
        today() + timedelta(days=1), TOMORROW_CALENDAR_HEADER, "Aucun événement demain."
    )


def _agenda(day: date, header: str, empty_text: str) -> str | None:
    if not _calendar_urls():
        return None  # not configured: skip the section silently

    calendars, failed = _fetch_calendars()
    if not calendars:
        raise RuntimeError("all calendars failed")

    events = _merged_events(calendars, day, ZoneInfo(config.TIMEZONE))
    lines = [header]
    if not events:
        lines.append(empty_text)
    for when, title in events:
        lines.append(f"{when}  {_escape(title)}")
    if failed:
        lines.append(f"⚠️ {failed} agenda(s) indisponible(s).")
    return "\n".join(lines)


def _load_deadlines() -> list:
    if config.DEADLINES_JSON:
        return json.loads(config.DEADLINES_JSON)
    for name in (config.DEADLINES_FILE, config.DEADLINES_FALLBACK_FILE):
        path = Path(name)
        if not path.is_absolute():
            path = BASE_DIR / path
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return []


DEADLINES_HEADER_PREFIX = "📅 <b>Échéances"


def get_deadlines() -> str:
    start = today()
    upcoming = []
    for item in _load_deadlines():
        due = date.fromisoformat(item["date"])
        days_left = (due - start).days
        if 0 <= days_left <= config.DEADLINES_DAYS:
            upcoming.append((days_left, due, item["title"]))
    upcoming.sort()

    header = f"{DEADLINES_HEADER_PREFIX} ({config.DEADLINES_DAYS} prochains jours)</b>"
    if not upcoming:
        return f"{header}\nRien à signaler. 🎉"

    lines = [header]
    for days_left, due, title in upcoming:
        if days_left == 0:
            when = "AUJOURD'HUI"
        elif days_left == 1:
            when = "demain"
        else:
            when = f"dans {days_left} jours"
        marker = "🔴" if days_left <= 2 else "🟡" if days_left <= 7 else "🟢"
        lines.append(f"{marker} {_escape(title)} : {format_short_date(due)} ({when})")
    return "\n".join(lines)


TOMORROW_DEADLINES_HEADER = "⏰ <b>À rendre demain</b>"


def get_tomorrow_deadlines() -> str | None:
    tomorrow = today() + timedelta(days=1)
    titles = sorted(
        item["title"] for item in _load_deadlines()
        if date.fromisoformat(item["date"]) == tomorrow
    )
    if not titles:
        return None  # nothing due tomorrow: omit the section
    return "\n".join([TOMORROW_DEADLINES_HEADER] + [f"• {_escape(t)}" for t in titles])


WEEKLY_DAY_PREFIX = "📆 <b>"  # e.g. "📆 <b>Lundi 23</b>"
WEEKLY_DEADLINES_HEADER = "⏰ <b>Échéances de la semaine</b>"


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'s' if n > 1 else ''}"


def build_weekly_sections() -> list[str]:
    """Summary of the coming Monday-Sunday: events grouped by day, deadlines
    of the week and a count line. Each part fails independently."""
    start = today() + timedelta(days=7 - today().weekday())  # next Monday
    end = start + timedelta(days=6)
    sections = [
        f"🗓 <b>Semaine du {format_long_date(start).rsplit(' ', 1)[0]}"
        f" au {format_long_date(end).rsplit(' ', 1)[0]}</b>"
    ]
    n_events = n_deadlines = 0
    unknown = False  # a part failed, so the week may not actually be free

    if _calendar_urls():
        try:
            calendars, failed = _fetch_calendars()
            if not calendars:
                raise RuntimeError("all calendars failed")
            tz = ZoneInfo(config.TIMEZONE)
            for offset in range(7):
                day = start + timedelta(days=offset)
                events = _merged_events(calendars, day, tz)
                if not events:
                    continue  # skip days without events
                n_events += len(events)
                lines = [f"{WEEKLY_DAY_PREFIX}{DAYS[day.weekday()].capitalize()} {day.day}</b>"]
                lines += [f"{when}  {_escape(title)}" for when, title in events]
                sections.append("\n".join(lines))
            if failed:
                sections.append(f"⚠️ {failed} agenda(s) indisponible(s).")
        except Exception as exc:
            print(f"[warn] weekly calendar failed: {type(exc).__name__}", file=sys.stderr)
            sections.append("⚠️ <b>Agenda</b> indisponible.")
            unknown = True

    try:
        due = sorted(
            (date.fromisoformat(item["date"]), item["title"])
            for item in _load_deadlines()
            if start <= date.fromisoformat(item["date"]) <= end
        )
        if due:
            n_deadlines = len(due)
            sections.append("\n".join(
                [WEEKLY_DEADLINES_HEADER]
                + [f"• {format_short_date(d)} : {_escape(t)}" for d, t in due]
            ))
    except Exception as exc:
        print(f"[warn] weekly deadlines failed: {type(exc).__name__}", file=sys.stderr)
        sections.append("⚠️ <b>Échéances</b> indisponibles.")
        unknown = True

    if n_events or n_deadlines or unknown:  # never claim a free week on errors
        sections.append(
            f"{_plural(n_events, 'événement')}, {_plural(n_deadlines, 'échéance')}."
        )
    else:
        sections.append("Semaine libre. 🎉")
    return sections


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def enabled_sources() -> list:
    sources = []
    if config.ENABLE_QURAN:
        sources.append(get_verse)
    if config.ENABLE_SELF_TALK:
        sources.append(get_self_talk)
    sources += [get_weather, get_calendar, get_deadlines]
    if config.ENABLE_WORD:
        sources.append(get_word)
    return sources


def evening_sources() -> list:
    sources = []
    if config.ENABLE_SELF_TALK:
        sources.append(get_challenge_reminder)
    if config.ENABLE_EVENING_VERSE:
        sources.append(get_evening_verse)
    sources += [get_tomorrow_calendar, get_tomorrow_deadlines]
    if config.ENABLE_NIGHT_NOTE:
        sources.append(get_night_note)  # always the last line
    return sources


def build_sections(evening: bool = False) -> list[str]:
    if evening:
        greeting = f"🌙 <b>Bonsoir</b> {format_long_date(today())}"
        sources = evening_sources()
    else:
        greeting = f"🌅 <b>Bonjour !</b> {format_long_date(today())}"
        sources = enabled_sources()
    sections = [greeting]
    for source in sources:
        try:
            section = source()
            if section is not None:  # None = section not configured
                sections.append(section)
        except Exception as exc:  # one failing source must not block the rest
            # Log only the error type/status: messages may contain URLs with
            # location or tokens, and Actions logs are public on public repos.
            status = getattr(getattr(exc, "response", None), "status_code", "")
            print(f"[warn] {source.__name__} failed: {type(exc).__name__} {status}",
                  file=sys.stderr)
            label = SOURCE_LABELS.get(source.__name__, source.__name__)
            sections.append(f"⚠️ <b>{label}</b> indisponible aujourd'hui.")
    return sections


def _redact(section: str) -> str:
    """Hide private content for public CI logs: self-talk, challenge, night
    note, calendar events and deadlines. Only headers are kept."""
    # Private text on the header line itself: keep the prefix only.
    for prefix in (CHALLENGE_HEADER, NIGHT_NOTE_HEADER):
        if section.startswith(prefix):
            return f"{prefix} [hidden in CI logs]"
    # Header line is not private (title or date): keep it, hide the rest.
    for prefix in (
        SELF_TALK_HEADER, WEEKLY_DAY_PREFIX,  # all 📆 calendar sections
        DEADLINES_HEADER_PREFIX, TOMORROW_DEADLINES_HEADER, WEEKLY_DEADLINES_HEADER,
    ):
        if section.startswith(prefix):
            return f"{section.splitlines()[0]}\n[hidden in CI logs]"
    return section


def split_messages(sections: list[str], limit: int = TELEGRAM_LIMIT) -> list[str]:
    """Join sections into as few messages as possible, splitting only at
    section boundaries. A single oversized section is cut as a last resort."""
    messages, current = [], ""
    for section in sections:
        while len(section) > limit:  # should not happen with normal content
            if current:
                messages.append(current)
                current = ""
            messages.append(section[:limit])
            section = section[limit:]
        candidate = f"{current}\n\n{section}" if current else section
        if len(candidate) <= limit:
            current = candidate
        else:
            messages.append(current)
            current = section
    if current:
        messages.append(current)
    return messages


def send(message: str) -> None:
    if not config.TELEGRAM_TOKEN or not config.TELEGRAM_CHAT_ID:
        raise RuntimeError("TELEGRAM_TOKEN and TELEGRAM_CHAT_ID must be set")
    resp = requests.post(
        f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
        json={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=15,
    )
    if not resp.ok:
        # Do not echo the URL: it contains the bot token.
        raise RuntimeError(f"Telegram API error {resp.status_code}: {resp.text}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="print the message instead of sending it"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--evening", action="store_true", help="build the evening message instead"
    )
    mode.add_argument(
        "--weekly", action="store_true", help="build the weekly summary instead"
    )
    args = parser.parse_args()

    if args.evening and not config.ENABLE_EVENING:
        print("Evening message disabled (ENABLE_EVENING=false).")
        return
    if args.weekly and not config.ENABLE_WEEKLY:
        print("Weekly summary disabled (ENABLE_WEEKLY=false).")
        return

    if args.weekly:
        sections = build_weekly_sections()
    else:
        sections = build_sections(evening=args.evening)
    if args.dry_run or config.DRY_RUN:
        if config.IN_CI:
            # Actions logs are public: never print private sections.
            sections = [_redact(s) for s in sections]
        messages = split_messages(sections)
        for i, message in enumerate(messages, 1):
            if len(messages) > 1:
                print(f"----- message {i}/{len(messages)} ({len(message)} chars) -----")
            print(message)
        return
    for message in split_messages(sections):
        send(message)
    print("Weekly summary sent." if args.weekly
          else "Evening message sent." if args.evening else "Brief sent.")


if __name__ == "__main__":
    main()
