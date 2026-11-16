"""Decide whether this workflow run should send a message, and which one.

GitHub cron schedules are in UTC only, so each message is scheduled at the two
UTC hours that can match the local target hour (with and without the clock
change). This script keeps only the run whose scheduled time falls on the
target local hour in TIMEZONE, and skips the other one silently.

Manual runs (workflow_dispatch) always send, using the MODE input.

Uses the standard library only, so it can run before dependencies are
installed. Writes `send` and `mode` to $GITHUB_OUTPUT when available.
"""

import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, "").strip() or default


def scheduled_utc(cron: str, now: datetime) -> datetime:
    """Most recent UTC time matching a daily cron like '0 20 * * *'.

    Using the scheduled time instead of the actual start time keeps the check
    correct when GitHub starts a run late."""
    minute, hour = (int(x) for x in cron.split()[:2])
    slot = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if slot > now:
        slot -= timedelta(days=1)
    return slot


def decide(event: str, cron: str, mode_input: str, tz_name: str,
           morning_hour: int, evening_hour: int, now: datetime) -> tuple[bool, str]:
    if event != "schedule":
        return True, mode_input if mode_input in ("morning", "evening") else "morning"
    local_hour = scheduled_utc(cron, now).astimezone(ZoneInfo(tz_name)).hour
    if local_hour == morning_hour:
        return True, "morning"
    if local_hour == evening_hour:
        return True, "evening"
    return False, ""


def main() -> None:
    send, mode = decide(
        event=_env("EVENT_NAME", "workflow_dispatch"),
        cron=_env("SCHEDULED_CRON"),
        mode_input=_env("MODE", "morning"),
        tz_name=_env("TIMEZONE", "Europe/Paris"),
        morning_hour=int(_env("MORNING_HOUR", "7")),
        evening_hour=int(_env("EVENING_HOUR", "21")),
        now=datetime.now(timezone.utc),
    )
    print(f"Sending the {mode} message." if send
          else "Not the target local hour for this slot: skipping.")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as fh:
            fh.write(f"send={'true' if send else 'false'}\nmode={mode}\n")


if __name__ == "__main__":
    main()
