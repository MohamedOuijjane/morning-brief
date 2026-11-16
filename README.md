# morning-brief

A small Python script, run by GitHub Actions, that sends a daily Telegram
message in the morning (weather, agenda, deadlines, verse and word of the day)
and a short one in the evening.

## Setup

1. Create a bot with **@BotFather** and get your chat ID.
2. Add the repository secrets `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID`.
   Optional settings are listed in `.env.example`.
3. Run the workflow from the **Actions** tab to test it.

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env
python main.py --dry-run
python main.py --evening --dry-run
```

## License

[MIT](LICENSE)
