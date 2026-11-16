"""HTTP GET with retries. Logs only a label and the error type, never URLs."""

import sys
import time
from typing import Any

import requests

HTTP_ATTEMPTS = 3
HTTP_TIMEOUT = 20  # seconds per attempt
HTTP_BACKOFF = 2.0  # seconds, doubled after each failed attempt


def http_get(
    url: str, params: dict[str, Any] | None = None, label: str = "request"
) -> requests.Response:
    """GET with retries on timeouts, connection errors, 429 and 5xx."""
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


def get_json(url: str, params: dict[str, Any] | None = None, label: str = "request") -> Any:
    return http_get(url, params=params, label=label).json()
