"""Settings loaded from environment variables."""

import os
from pathlib import Path


def _load_dotenv(path: Path = Path(__file__).parent / ".env") -> None:
    """Minimal .env loader for local runs. Existing env vars take priority."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


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
# Raw JSON content takes priority over the file path (used by the workflow).
DEADLINES_JSON = _get("DEADLINES_JSON")
DEADLINES_FILE = _get("DEADLINES_FILE", "deadlines.json")
DEADLINES_FALLBACK_FILE = "deadlines.example.json"

def _flag(name: str, default: str) -> bool:
    return _get(name, default).lower() in ("1", "true", "yes", "on")


DRY_RUN = _flag("DRY_RUN", "false")

# Optional sections
ENABLE_QURAN = _flag("ENABLE_QURAN", "true")
ENABLE_WORD = _flag("ENABLE_WORD", "true")
WORDS_FILE = _get("WORDS_FILE", "words.json")

# Self-talk messages are private: raw JSON from a secret, else the local
# (git-ignored) file, else the committed placeholder example.
ENABLE_SELF_TALK = _flag("ENABLE_SELF_TALK", "true")
SELF_TALK_JSON = _get("SELF_TALK_JSON")
SELF_TALK_FILE = _get("SELF_TALK_FILE", "self_talk.json")
SELF_TALK_FALLBACK_FILE = "self_talk.example.json"

# Secret iCal URLs: GCAL_ICS_URLS holds one per line (blank lines and lines
# starting with # are ignored); GCAL_ICS_URL is accepted as one more URL.
# If neither is set, the agenda section is skipped.
GCAL_ICS_URLS = os.environ.get("GCAL_ICS_URLS", "")
GCAL_ICS_URL = _get("GCAL_ICS_URL")

# Set by GitHub Actions; used to keep private content out of public logs.
IN_CI = _get("GITHUB_ACTIONS").lower() == "true"
