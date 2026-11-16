"""Shared fixtures: no network, no private files, a frozen clock."""

import os

os.environ["BRIEF_NO_DOTENV"] = "1"  # never load a local .env in tests

from collections.abc import Callable, Iterator  # noqa: E402
from datetime import datetime  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402
from zoneinfo import ZoneInfo  # noqa: E402

import pytest  # noqa: E402
import requests  # noqa: E402

from brief import config, http, utils  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def isolated(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Block real HTTP and point every data source at fake data only."""

    def blocked(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("network access is blocked in tests")

    monkeypatch.setattr(requests.sessions.Session, "request", blocked)
    monkeypatch.setattr(http, "HTTP_BACKOFF", 0)

    settings: dict[str, Any] = {
        "TIMEZONE": "Europe/Paris",
        "CITY_NAME": "Paris",
        "TELEGRAM_TOKEN": "",
        "TELEGRAM_CHAT_ID": "",
        "DEADLINES_DAYS": 14,
        "DEADLINES_JSON": "",
        "DEADLINES_FILE": str(FIXTURES / "deadlines.json"),
        "SELF_TALK_JSON": "",
        "SELF_TALK_FILE": "self_talk.example.json",
        "NIGHT_NOTES_JSON": "",
        "NIGHT_NOTES_FILE": "night_notes.example.json",
        "WORDS_JSON": "",
        "WORDS_FILE": "words.example.json",
        "GCAL_ICS_URLS": "",
        "GCAL_ICS_URL": "",
        "ENABLE_QURAN": True,
        "ENABLE_SELF_TALK": True,
        "ENABLE_WORD": True,
        "ENABLE_EVENING": True,
        "ENABLE_EVENING_VERSE": True,
        "ENABLE_NIGHT_NOTE": True,
        "ENABLE_WEEKLY": True,
        "IN_CI": False,
        "DRY_RUN": False,
    }
    for name, value in settings.items():
        monkeypatch.setattr(config, name, value)
    yield


@pytest.fixture(autouse=True)
def freeze(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], None]:
    """Freeze the clock. Default: Monday 16 November 2026, 08:00 in Paris.
    Call freeze("2026-11-16T23:30:00+00:00") to move it."""

    def _freeze(iso: str) -> None:
        moment = datetime.fromisoformat(iso)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=ZoneInfo("Europe/Paris"))
        monkeypatch.setattr(utils, "now", lambda: moment.astimezone(ZoneInfo(config.TIMEZONE)))

    _freeze("2026-11-16T08:00:00")
    return _freeze


class FakeResponse:
    def __init__(self, status: int = 200, content: bytes = b"", data: Any = None) -> None:
        self.status_code = status
        self.content = content
        self._data = data
        self.ok = status < 400
        self.text = content.decode("utf-8", "replace")

    def json(self) -> Any:
        return self._data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)  # type: ignore[arg-type]


@pytest.fixture
def fake_get(monkeypatch: pytest.MonkeyPatch) -> Callable[[dict[str, Any]], list[str]]:
    """Route requests.get by URL. Each route value is a FakeResponse, an
    exception instance, or a list of those (consumed in order).
    Returns the list of requested URLs."""

    def install(routes: dict[str, Any]) -> list[str]:
        calls: list[str] = []

        def get(url: str, params: Any = None, timeout: float | None = None) -> FakeResponse:
            calls.append(url)
            if url not in routes:
                raise requests.ConnectionError("no route")
            outcome = routes[url]
            if isinstance(outcome, list):
                outcome = outcome.pop(0) if len(outcome) > 1 else outcome[0]
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        monkeypatch.setattr(requests, "get", get)
        return calls

    return install


def ics_response(name: str) -> FakeResponse:
    return FakeResponse(content=(FIXTURES / name).read_bytes())
