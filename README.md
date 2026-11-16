# morning-brief

[![CI](https://github.com/MohamedOuijjane/morning-brief/actions/workflows/ci.yml/badge.svg)](https://github.com/MohamedOuijjane/morning-brief/actions/workflows/ci.yml)

A Telegram bot that sends scheduled daily summaries, run entirely by GitHub
Actions with no server. All personal data comes from repository secrets, so
the code stays public while the content stays private.

## Setup

1. Create a bot with @BotFather and note your chat ID.
2. Add `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` and `TIMEZONE` as repository secrets.
3. Add your data as secrets (see `.env.example` for the names).
4. Run the **Morning brief** workflow from the Actions tab to test it.

## License

[MIT](LICENSE)
