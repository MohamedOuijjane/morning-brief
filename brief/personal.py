"""Private personal sections: self-talk, challenge reminder, bedtime note.

Content comes from a secret (raw JSON), else a git-ignored local file, else
a committed placeholder example. It is never printed in CI logs."""

from typing import Any

from brief import config, utils

SELF_TALK_HEADER = "💬 <b>كلمة لنفسك اليوم</b>"
CHALLENGE_HEADER = "🎯 <b>تحدّي اليوم:</b>"
NIGHT_NOTE_HEADER = "🌃 <b>قبل النوم:</b>"


def todays_self_talk() -> dict[str, Any]:
    """Same date-based pick for the morning message and the evening reminder."""
    messages = utils.load_json(
        config.SELF_TALK_JSON, config.SELF_TALK_FILE, config.SELF_TALK_FALLBACK_FILE
    )
    return utils.pick_by_date(messages, utils.today())


def get_self_talk() -> str:
    msg = todays_self_talk()
    return "\n".join([
        SELF_TALK_HEADER,
        f"« {utils.escape(msg['title'])} »",
        utils.escape(msg["body"]),
        f"{CHALLENGE_HEADER} {utils.escape(msg['challenge'])}",
    ])


def get_challenge_reminder() -> str:
    msg = todays_self_talk()
    return f"{CHALLENGE_HEADER} {utils.escape(msg['challenge'])}\nهل فعلته؟"


def get_night_note() -> str:
    notes = utils.load_json(
        config.NIGHT_NOTES_JSON, config.NIGHT_NOTES_FILE, config.NIGHT_NOTES_FALLBACK_FILE
    )
    return f"{NIGHT_NOTE_HEADER} {utils.escape(utils.pick_by_date(notes, utils.today()))}"
