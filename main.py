"""Morning brief: today's weather and upcoming deadlines, sent to Telegram.

The message itself is in French; dates are formatted with hardcoded name
lists so the output does not depend on the system locale.
"""

import argparse
import json
import sys
import time
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

import config

BASE_DIR = Path(__file__).parent

WEATHER_ATTEMPTS = 3
WEATHER_TIMEOUT = 20  # seconds per attempt
WEATHER_BACKOFF = 2  # seconds, doubled after each failed attempt

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
SOURCE_LABELS = {"get_weather": "Météo", "get_deadlines": "Échéances"}


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


def _fetch_forecast() -> dict:
    """Call Open-Meteo, retrying on timeouts, connection errors, 429 and 5xx."""
    params = {
        "latitude": config.LATITUDE,
        "longitude": config.LONGITUDE,
        "timezone": config.TIMEZONE,
        "current": "temperature_2m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
        "precipitation_probability_max,wind_speed_10m_max",
        "forecast_days": 1,
    }
    delay = WEATHER_BACKOFF
    for attempt in range(1, WEATHER_ATTEMPTS + 1):
        try:
            resp = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params=params,
                timeout=WEATHER_TIMEOUT,
            )
            if resp.status_code == 429 or resp.status_code >= 500:
                resp.raise_for_status()
            break
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
            if attempt == WEATHER_ATTEMPTS:
                raise
            status = getattr(exc.response, "status_code", "")
            print(
                f"[retry] get_weather attempt {attempt} failed: "
                f"{type(exc).__name__} {status}, retrying in {delay}s",
                file=sys.stderr,
            )
            time.sleep(delay)
            delay *= 2
    resp.raise_for_status()  # other 4xx (e.g. bad coordinates): no retry
    return resp.json()


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


def get_deadlines() -> str:
    start = today()
    upcoming = []
    for item in _load_deadlines():
        due = date.fromisoformat(item["date"])
        days_left = (due - start).days
        if 0 <= days_left <= config.DEADLINES_DAYS:
            upcoming.append((days_left, due, item["title"]))
    upcoming.sort()

    header = f"📅 <b>Échéances ({config.DEADLINES_DAYS} prochains jours)</b>"
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


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_message() -> str:
    sections = [f"🌅 <b>Bonjour !</b> {format_long_date(today())}"]
    for source in (get_weather, get_deadlines):
        try:
            sections.append(source())
        except Exception as exc:  # one failing source must not block the rest
            # Log only the error type/status: messages may contain URLs with
            # location or tokens, and Actions logs are public on public repos.
            status = getattr(getattr(exc, "response", None), "status_code", "")
            print(f"[warn] {source.__name__} failed: {type(exc).__name__} {status}",
                  file=sys.stderr)
            label = SOURCE_LABELS.get(source.__name__, source.__name__)
            sections.append(f"⚠️ <b>{label}</b> indisponible aujourd'hui.")
    return "\n\n".join(sections)


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
    args = parser.parse_args()

    message = build_message()
    if args.dry_run or config.DRY_RUN:
        print(message)
        return
    send(message)
    print("Message sent.")


if __name__ == "__main__":
    main()
