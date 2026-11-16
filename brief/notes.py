"""Daily note (morning, with its challenge reminded in the evening) and
closing note (end of the evening message).

Both come from a secret or a local file. They are skipped when no data is
configured, and never printed in CI logs."""

from typing import Any

from brief import config, utils

DAILY_NOTE_HEADER = "💬 <b>كلمة لنفسك اليوم</b>"
CHALLENGE_HEADER = "🎯 <b>تحدّي اليوم:</b>"
CLOSING_NOTE_HEADER = "🌃 <b>قبل النوم:</b>"


def todays_daily_note() -> dict[str, Any] | None:
    """Same date-based pick for the morning note and the evening reminder."""
    notes = utils.load_json(config.DAILY_NOTE_JSON, config.DAILY_NOTE_FILE)
    return utils.pick_by_date(notes, utils.today()) if notes else None


def get_daily_note() -> str | None:
    note = todays_daily_note()
    if note is None:
        return None
    return "\n".join([
        DAILY_NOTE_HEADER,
        f"« {utils.escape(note['title'])} »",
        utils.escape(note["body"]),
        f"{CHALLENGE_HEADER} {utils.escape(note['challenge'])}",
    ])


def get_challenge_reminder() -> str | None:
    note = todays_daily_note()
    if note is None:
        return None
    return f"{CHALLENGE_HEADER} {utils.escape(note['challenge'])}\nهل فعلته؟"


def get_closing_note() -> str | None:
    notes = utils.load_json(config.CLOSING_NOTE_JSON, config.CLOSING_NOTE_FILE)
    if not notes:
        return None
    return f"{CLOSING_NOTE_HEADER} {utils.escape(utils.pick_by_date(notes, utils.today()))}"
