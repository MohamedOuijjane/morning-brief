"""HTTP retries, weather formatting and Telegram sending, all mocked."""

import pytest
import requests

from brief import config, http, telegram, weather
from tests.conftest import FakeResponse

URL = "https://api.test.invalid/data"


def test_retries_timeouts_then_succeeds(fake_get, capsys) -> None:
    calls = fake_get({URL: [requests.Timeout(), FakeResponse(503), FakeResponse(data={"ok": 1})]})
    assert http.get_json(URL, label="demo") == {"ok": 1}
    assert len(calls) == 3
    log = capsys.readouterr().err
    assert "demo attempt 1 failed: Timeout" in log and "test.invalid" not in log


def test_gives_up_after_three_attempts(fake_get) -> None:
    calls = fake_get({URL: [requests.ConnectionError()]})
    with pytest.raises(requests.ConnectionError):
        http.get_json(URL)
    assert len(calls) == http.HTTP_ATTEMPTS


def test_client_errors_are_not_retried(fake_get) -> None:
    calls = fake_get({URL: [FakeResponse(404)]})
    with pytest.raises(requests.HTTPError):
        http.get_json(URL)
    assert len(calls) == 1


def test_network_is_blocked_by_default() -> None:
    with pytest.raises(RuntimeError, match="blocked"):
        requests.Session().get(URL)


def test_weather_in_french(fake_get) -> None:
    data = {
        "current": {"temperature_2m": 10.9},
        "daily": {
            "weather_code": [61], "temperature_2m_min": [6.2], "temperature_2m_max": [11.4],
            "precipitation_probability_max": [80], "wind_speed_10m_max": [14.0],
        },
    }
    fake_get({weather.FORECAST_API: FakeResponse(data=data)})
    assert weather.get_weather().splitlines() == [
        "🌧 <b>Météo à Sample City</b>",
        "Pluie faible",
        "Actuellement : 10,9 °C",
        "Min / Max : 6,2 °C / 11,4 °C",
        "Risque de pluie : 80 %",
        "Vent : jusqu'à 14,0 km/h",
    ]


def test_send_requires_credentials() -> None:
    with pytest.raises(RuntimeError, match="must be set"):
        telegram.send("hi")


def test_send_posts_html_message(monkeypatch) -> None:
    monkeypatch.setattr(config, "TELEGRAM_TOKEN", "123:FAKE")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "42")
    posted: dict = {}

    def fake_post(url: str, json: dict, timeout: float) -> FakeResponse:
        posted.update(url=url, json=json)
        return FakeResponse(200)

    monkeypatch.setattr(requests, "post", fake_post)
    telegram.send("<b>hi</b>")
    assert posted["url"].endswith("/bot123:FAKE/sendMessage")
    assert posted["json"]["chat_id"] == "42" and posted["json"]["parse_mode"] == "HTML"


def test_send_error_does_not_include_token(monkeypatch) -> None:
    monkeypatch.setattr(config, "TELEGRAM_TOKEN", "123:FAKE")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResponse(401, b'{"ok":false}'))
    with pytest.raises(RuntimeError) as err:
        telegram.send("hi")
    assert "FAKE" not in str(err.value)
