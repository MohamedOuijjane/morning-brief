"""Morning brief: today's weather and upcoming deadlines, sent to Telegram."""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

import config

BASE_DIR = Path(__file__).parent

# WMO weather interpretation codes used by Open-Meteo.
WEATHER_CODES = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫"),
    48: ("Rime fog", "🌫"),
    51: ("Light drizzle", "🌦"),
    53: ("Drizzle", "🌦"),
    55: ("Dense drizzle", "🌦"),
    56: ("Freezing drizzle", "🌧"),
    57: ("Freezing drizzle", "🌧"),
    61: ("Light rain", "🌧"),
    63: ("Rain", "🌧"),
    65: ("Heavy rain", "🌧"),
    66: ("Freezing rain", "🌧"),
    67: ("Freezing rain", "🌧"),
    71: ("Light snow", "🌨"),
    73: ("Snow", "🌨"),
    75: ("Heavy snow", "❄️"),
    77: ("Snow grains", "🌨"),
    80: ("Light showers", "🌦"),
    81: ("Showers", "🌧"),
    82: ("Violent showers", "⛈"),
    85: ("Snow showers", "🌨"),
    86: ("Heavy snow showers", "❄️"),
    95: ("Thunderstorm", "⛈"),
    96: ("Thunderstorm with hail", "⛈"),
    99: ("Thunderstorm with hail", "⛈"),
}


def today() -> date:
    return datetime.now(ZoneInfo(config.TIMEZONE)).date()


def get_weather() -> str:
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": config.LATITUDE,
            "longitude": config.LONGITUDE,
            "timezone": config.TIMEZONE,
            "current": "temperature_2m,weather_code",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
            "precipitation_probability_max,wind_speed_10m_max",
            "forecast_days": 1,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    daily = data["daily"]
    current = data.get("current", {})

    code = daily["weather_code"][0]
    label, icon = WEATHER_CODES.get(code, ("Unknown", "🌡"))
    lines = [
        f"{icon} <b>Weather in {config.CITY_NAME}</b>",
        f"{label}",
        f"Now: {current.get('temperature_2m', '?')}°C",
        f"Min / Max: {daily['temperature_2m_min'][0]}°C / {daily['temperature_2m_max'][0]}°C",
        f"Rain chance: {daily['precipitation_probability_max'][0]}%",
        f"Wind: up to {daily['wind_speed_10m_max'][0]} km/h",
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

    header = f"📅 <b>Deadlines (next {config.DEADLINES_DAYS} days)</b>"
    if not upcoming:
        return f"{header}\nNothing due. 🎉"

    lines = [header]
    for days_left, due, title in upcoming:
        if days_left == 0:
            when = "TODAY"
        elif days_left == 1:
            when = "tomorrow"
        else:
            when = f"in {days_left} days"
        marker = "🔴" if days_left <= 2 else "🟡" if days_left <= 7 else "🟢"
        lines.append(f"{marker} {_escape(title)}: {due:%a %d %b} ({when})")
    return "\n".join(lines)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_message() -> str:
    sections = [f"🌅 <b>Good morning!</b> {today():%A %d %B %Y}"]
    for source in (get_weather, get_deadlines):
        try:
            sections.append(source())
        except Exception as exc:  # one failing source must not block the rest
            name = source.__name__.removeprefix("get_").capitalize()
            # Log only the error type/status: messages may contain URLs with
            # location or tokens, and Actions logs are public on public repos.
            status = getattr(getattr(exc, "response", None), "status_code", "")
            print(f"[warn] {source.__name__} failed: {type(exc).__name__} {status}",
                  file=sys.stderr)
            sections.append(f"⚠️ <b>{name}</b> unavailable today.")
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
