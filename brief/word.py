"""Word of the day in Arabic, French and English.

The word list is private, like self-talk: WORDS_JSON (secret), else a
git-ignored local words.json, else the committed words.example.json."""

from brief import config, utils

WORD_HEADER = "💬 <b>Mot du jour</b>"


def get_word() -> str:
    words = utils.load_json(config.WORDS_JSON, config.WORDS_FILE, config.WORDS_FALLBACK_FILE)
    word = words[utils.today().timetuple().tm_yday % len(words)]
    e = utils.escape
    return "\n".join([
        WORD_HEADER,
        f"🇸🇦 <b>{e(word['ar'])}</b> — {e(word['ar_example'])}",
        f"🇫🇷 <b>{e(word['fr'])}</b> — {e(word['fr_example'])}",
        f"🇬🇧 <b>{e(word['en'])}</b> — {e(word['en_example'])}",
    ])
