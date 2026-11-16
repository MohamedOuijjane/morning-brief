"""Settings loaded from environment variables.

Every module reads settings as ``config.NAME`` at call time, so tests can
override them with ``monkeypatch.setattr(config, "NAME", value)``.
"""

import os
from pathlib import Path

# Repository root: local data files (git-ignored) are looked up here.
ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path = ROOT / ".env") -> None:
    """Minimal .env loader for local runs. Existing env vars take priority."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


if os.environ.get("BRIEF_NO_DOTENV") != "1":  # set by the test suite
    _load_dotenv()


def _get(name: str, default: str = "") -> str:
    value = os.environ.get(name, "").strip()
    return value or default


TELEGRAM_TOKEN = _get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = _get("TELEGRAM_CHAT_ID")

LATITUDE = float(_get("LATITUDE", "48.8566"))
LONGITUDE = float(_get("LONGITUDE", "2.3522"))
CITY_NAME = _get("CITY_NAME", "Paris")
TIMEZONE = _get("TIMEZONE", "Europe/Paris")

DEADLINES_DAYS = int(_get("DEADLINES_DAYS", "14"))


def _flag(name: str, default: str) -> bool:
    return _get(name, default).lower() in ("1", "true", "yes", "on")


DRY_RUN = _flag("DRY_RUN", "false")

# Data sources. Each one is read from raw JSON in an environment variable
# (a GitHub secret in Actions), else from a local git-ignored file. When
# neither exists, the section that needs it is skipped.
DEADLINES_JSON = _get("DEADLINES_JSON")
DEADLINES_FILE = _get("DEADLINES_FILE", "deadlines.json")
WORDS_JSON = _get("WORDS_JSON")
WORDS_FILE = _get("WORDS_FILE", "words.json")
DAILY_NOTE_JSON = _get("DAILY_NOTE_JSON")
DAILY_NOTE_FILE = _get("DAILY_NOTE_FILE", "daily_note.json")
CLOSING_NOTE_JSON = _get("CLOSING_NOTE_JSON")
CLOSING_NOTE_FILE = _get("CLOSING_NOTE_FILE", "closing_note.json")
EVENING_VERSES_JSON = _get("EVENING_VERSES_JSON")
EVENING_VERSES_FILE = _get("EVENING_VERSES_FILE", "evening_verses.json")

# Secret iCal URLs: GCAL_ICS_URLS holds one per line (blank lines and lines
# starting with # are ignored); GCAL_ICS_URL is accepted as one more URL.
GCAL_ICS_URLS = os.environ.get("GCAL_ICS_URLS", "")
GCAL_ICS_URL = _get("GCAL_ICS_URL")

# Section toggles
ENABLE_QURAN = _flag("ENABLE_QURAN", "true")
ENABLE_DAILY_NOTE = _flag("ENABLE_DAILY_NOTE", "true")
ENABLE_WORD = _flag("ENABLE_WORD", "true")
ENABLE_EVENING = _flag("ENABLE_EVENING", "true")
ENABLE_EVENING_VERSE = _flag("ENABLE_EVENING_VERSE", "true")
ENABLE_CLOSING_NOTE = _flag("ENABLE_CLOSING_NOTE", "true")
ENABLE_WEEKLY = _flag("ENABLE_WEEKLY", "true")

# Set by GitHub Actions; used to keep private content out of public logs.
IN_CI = _get("GITHUB_ACTIONS").lower() == "true"
