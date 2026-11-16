# morning-brief

A small Python script that runs every morning on GitHub Actions and sends one
Telegram message with:

1. **Verse of the day**: one ayah in Arabic with its Tafsir Al-Muyassar, from
   [alquran.cloud](https://alquran.cloud/api) (free, no API key)
2. **Today's weather** from [Open-Meteo](https://open-meteo.com/) (free, no API key)
3. **Upcoming deadlines** due in the next 14 days, read from a JSON file
4. **Word of the day** in Arabic, French and English, with an example sentence

Each source is fetched on its own, so if the weather API is down you still
get the rest of the message. API requests are retried up to 3 times with a
short backoff on timeouts, rate limits and server errors. If the brief is longer
than Telegram's 4096-character limit, it is split into several messages at
section boundaries.

The message is written in French. Dates are formatted with built-in day and
month names, so no `fr_FR` system locale is needed.

```
🌅 Bonjour ! lundi 16 novembre 2026

📖 آية اليوم
﴿ ثُمَّ إِنَّكُمْ يَوْمَ ٱلْقِيَٰمَةِ عِندَ رَبِّكُمْ تَخْتَصِمُونَ ﴾
سُورَةُ الزُّمَرِ — الآية 31
التفسير: إنك -أيها الرسول- ميت وإنهم ميتون، ثم إنكم جميعًا- أيها الناس- يوم القيامة عند ربكم تتنازعون، فيحكم بينكم بالعدل والإنصاف.

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

💬 Mot du jour
🇸🇦 أسبوع — الامتحان في الأسبوع القادم.
🇫🇷 semaine — L'examen est la semaine prochaine.
🇬🇧 week — The exam is next week.
```

## Project layout

| File | Purpose |
| --- | --- |
| `main.py` | `get_verse()`, `get_weather()`, `get_deadlines()`, `get_word()`, `send()` |
| `words.json` | 150 words in Arabic, French and English with example sentences |
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

## Verse and word of the day

- **Verse**: picked from the date, so reruns on the same day show the same
  ayah, and over time it cycles through all 6236 ayahs. Ayahs longer than 400
  characters are skipped in favour of the next one. The verse and the tafsir
  are shown exactly as returned by the API.
- **Word**: picked by day of the year from `words.json`. Add or edit entries
  freely; each needs `ar`, `fr`, `en`, `ar_example`, `fr_example` and
  `en_example`.

Both sections can be turned off with `ENABLE_QURAN=false` or `ENABLE_WORD=false`
(as a secret or variable in GitHub, or in `.env` locally).

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
| `ENABLE_QURAN` | `true` | Show the verse of the day |
| `ENABLE_WORD` | `true` | Show the word of the day |
| `WORDS_FILE` | `words.json` | Word list |
| `DRY_RUN` | `false` | Print instead of sending |

## License

[MIT](LICENSE)
