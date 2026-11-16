"""Local-hour send guard. Europe/London switches between UTC+0 and UTC+1,
like the two UTC hours scheduled in the workflow."""

from datetime import UTC, datetime, timedelta

import pytest

import schedule_check
from schedule_check import decide, scheduled_utc

CRONS = ["0 6 * * *", "0 7 * * *", "0 20 * * *", "0 21 * * *", "0 19 * * 0", "0 20 * * 0"]
TZ = "Europe/London"


def run(day: tuple[int, int, int], cron: str, delay_min: int = 0) -> tuple[bool, str]:
    minute, hour = (int(x) for x in cron.split()[:2])
    now = datetime(*day, hour, minute, tzinfo=UTC) + timedelta(minutes=delay_min)
    return decide("schedule", cron, "", TZ, 7, 21, now, weekly_hour=20)


def sends(day: tuple[int, int, int]) -> dict[str, str]:
    return {cron: mode for cron in CRONS for ok, mode in [run(day, cron)] if ok}


def test_winter_sunday_utc_plus_0() -> None:
    assert sends((2026, 11, 22)) == {
        "0 7 * * *": "morning", "0 21 * * *": "evening", "0 20 * * 0": "weekly",
    }


def test_summer_sunday_utc_plus_1() -> None:
    assert sends((2026, 7, 5)) == {
        "0 6 * * *": "morning", "0 20 * * *": "evening", "0 19 * * 0": "weekly",
    }


def test_no_weekly_on_other_days() -> None:
    assert set(sends((2026, 11, 23)).values()) == {"morning", "evening"}


def test_late_start_still_counts_as_its_slot() -> None:
    assert run((2026, 11, 16), "0 21 * * *", delay_min=90) == (True, "evening")  # after midnight
    assert run((2026, 11, 16), "0 20 * * *", delay_min=75) == (False, "")


def test_scheduled_slot_is_the_most_recent_one() -> None:
    now = datetime(2026, 11, 17, 0, 30, tzinfo=UTC)
    assert scheduled_utc("0 21 * * *", now) == datetime(2026, 11, 16, 21, 0, tzinfo=UTC)


@pytest.mark.parametrize(("mode", "expected"), [("evening", "evening"), ("weekly", "weekly"),
                                                ("", "morning"), ("bogus", "morning")])
def test_manual_runs_always_send(mode: str, expected: str) -> None:
    assert decide("workflow_dispatch", "", mode, TZ, 7, 21, datetime.now(UTC)) == (True, expected)


def test_writes_github_output(monkeypatch, tmp_path, capsys) -> None:
    out = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setenv("EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("MODE", "weekly")
    schedule_check.main()
    assert out.read_text() == "send=true\nmode=weekly\n"
    assert capsys.readouterr().out.strip() == "Sending the weekly message."
