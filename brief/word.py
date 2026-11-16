"""Word of the day in three languages, from WORDS_JSON or a local file."""

from brief import config, utils

WORD_HEADER = "💬 <b>Mot du jour</b>"


def get_word() -> str | None:
    words = utils.load_json(config.WORDS_JSON, config.WORDS_FILE)
    if not words:
        return None  # no word list configured
    word = words[utils.today().timetuple().tm_yday % len(words)]
    e = utils.escape
    return "\n".join([
        WORD_HEADER,
        f"🇸🇦 <b>{e(word['ar'])}</b> — {e(word['ar_example'])}",
        f"🇫🇷 <b>{e(word['fr'])}</b> — {e(word['fr_example'])}",
        f"🇬🇧 <b>{e(word['en'])}</b> — {e(word['en_example'])}",
    ])
