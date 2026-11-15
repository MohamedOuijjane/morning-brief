# morning-brief

A small Python script that runs every morning on GitHub Actions and sends one
Telegram message with:

1. **Today's weather** from [Open-Meteo](https://open-meteo.com/) (free, no API key)
2. **Upcoming deadlines** due in the next 14 days, read from a JSON file

Each source is fetched on its own, so if the weather API is down you still
get your deadlines (and the other way around). Weather requests are retried
up to 3 times with a short backoff on timeouts, rate limits and server errors.

The message is written in French. Dates are formatted with built-in day and
month names, so no `fr_FR` system locale is needed.

```
🌅 Bonjour ! lundi 16 novembre 2026

🌧 Météo à Paris
Pluie faible
Actuellement : 10,8 °C
Min / Max : 10,4 °C / 13,8 °C
Risque de pluie : 100 %
Vent : jusqu'à 18,0 km/h

📅 Échéances (14 prochains jours)
🔴 Submit sample project report : mar. 17 nov. (demain)
🟡 Pay example utility bill : ven. 20 nov. (dans 4 jours)
🟢 Renew placeholder library card : jeu. 26 nov. (dans 10 jours)
```

## Project layout

| File | Purpose |
| --- | --- |
| `main.py` | `get_weather()`, `get_deadlines()`, `send()` |
| `config.py` | Reads all settings from environment variables |
| `deadlines.example.json` | Sample deadlines (fake data) |
| `.env.example` | Variable names for local runs |
| `.github/workflows/morning.yml` | Daily schedule + manual trigger |

## Setup

### 1. Create a Telegram bot

1. Open Telegram and start a chat with **@BotFather**.
2. Send `/newbot`, choose a display name and a username ending in `bot`.
3. BotFather replies with a **bot token**. Keep it private: anyone with it
   can control your bot.

### 2. Get your chat ID

1. Open a chat with your new bot and send it any message (e.g. `hi`).
2. Open this URL in your browser, replacing `<TOKEN>` with your bot token:

   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```

3. In the JSON response, find `"chat":{"id": ...}`. That number is your
   **chat ID**.

### 3. Fork or clone this repository

```bash
git clone https://github.com/<your-username>/morning-brief.git
cd morning-brief
```

### 4. Add GitHub secrets

In your repository go to **Settings → Secrets and variables → Actions →
New repository secret** and add:

| Secret | Required | Value |
| --- | --- | --- |
| `TELEGRAM_TOKEN` | yes | Bot token from BotFather |
| `TELEGRAM_CHAT_ID` | yes | Your chat ID |
| `DEADLINES_JSON` | no | Full content of your deadlines file (see below) |
| `LATITUDE`, `LONGITUDE`, `CITY_NAME`, `TIMEZONE` | no | Your location |

If the location is not set, the script defaults to Paris
(`48.8566`, `2.3522`, `Europe/Paris`). Location values can also be set as
**variables** (Variables tab) instead of secrets if you don't mind them being
visible to repo collaborators.

If `DEADLINES_JSON` is not set, the workflow falls back to
`deadlines.example.json`.

### 5. Test it

Go to **Actions → Morning brief → Run workflow**. You should receive the
message within a minute. After that it runs automatically every day at
06:00 UTC (edit the `cron` line in `.github/workflows/morning.yml` to change it).

## Deadlines format

```json
[
  { "title": "Submit sample project report", "date": "2026-11-17" },
  { "title": "Pay example utility bill", "date": "2026-11-20" }
]
```

Dates use `YYYY-MM-DD`. Only items due between today and 14 days from now are
shown (change with `DEADLINES_DAYS`).

To keep your real deadlines private, put them in `deadlines.json` locally
(ignored by git) and paste the same content into the `DEADLINES_JSON` secret.

## Running locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env                       # then fill in your values
cp deadlines.example.json deadlines.json   # then add your real deadlines

python main.py --dry-run   # print the message instead of sending it
python main.py             # send it to Telegram
```

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `TELEGRAM_TOKEN` | – | Bot token |
| `TELEGRAM_CHAT_ID` | – | Destination chat |
| `LATITUDE` / `LONGITUDE` | `48.8566` / `2.3522` | Weather location |
| `CITY_NAME` | `Paris` | Name shown in the message |
| `TIMEZONE` | `Europe/Paris` | Used for "today" and the forecast |
| `DEADLINES_JSON` | – | Deadlines as raw JSON (takes priority) |
| `DEADLINES_FILE` | `deadlines.json` | Deadlines file, falls back to the example |
| `DEADLINES_DAYS` | `14` | Look-ahead window |
| `DRY_RUN` | `false` | Print instead of sending |

## License

[MIT](LICENSE)
