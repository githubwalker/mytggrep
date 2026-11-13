# mytggrep

A Telegram "grep": it watches chosen channels and groups from **your own Telegram account**. When a message matches your filters, a **bot** reposts the message to your channel. Each repost shows:

- the source chat's name, which links to the original message
- the author
- the original text with its formatting; a text too long for one Telegram message is split into several

The bot is there for notifications: Telegram doesn't notify you about posts you made yourself, so reposts from your own account would arrive silently. Posts from the bot notify you like any other channel post.

## Required files

> **Before you run or deploy, put both files in the project root, next to `main.py`:**
>
> ```
> mytggrep/
> ├── .env                  ← create it yourself
> ├── my_account.session    ← create it yourself
> ├── main.py
> └── ...
> ```
>
> Neither file is in git, because both are secrets. A fresh clone doesn't have them, so you have to add them to every machine yourself, including the server. Without `.env` the app stops at startup. Without `my_account.session` the app asks for a Telegram login, which can't be answered on a server or in Docker. The Docker build also fails if either file is missing.

### `.env`: settings

`.env` holds your Telegram API credentials, the chats to watch, where to send matches, and the filter settings. To create it, copy `.env.example` and fill in the values:

```env
# From https://my.telegram.org → API development tools
API_ID=12345678
API_HASH=0123456789abcdef0123456789abcdef

# Bot that sends the reposts (from @BotFather, see below)
BOT_TOKEN=1234567890:AAAbbbCCCdddEEEfffGGGhhhIIIjjjKKKlll

# Chats to watch: IDs of private chats (with the -100 prefix) or @usernames of public ones
CHANNELS_TO_MONITOR=["-1001234567890", "@public_channel"]

# Where matches are sent: ID of a channel or group where the bot is an admin
MY_DESTINATION=-1001234567890

# Preliminary filter (see below)
PRELIMINARY_FILTER='("куплю" or "ищу") and ("рубл" or "RUB") and ("динар" or "RSD")'

# Azure OpenAI
AI_ENDPOINT="https://your-resource.openai.azure.com/"
AI_MODEL_NAME="your-model"
AI_DEPLOYMENT="your-deployment"
AI_SUBSCRIPTION_KEY="your-azure-openai-key"
# API version, e.g. "2024-12-01-preview" (Azure OpenAI models),
# or "v1" for the version-less v1 API (recommended for Foundry models like Kimi, DeepSeek...;
# a Foundry project URL like https://res.services.ai.azure.com/api/projects/proj works as AI_ENDPOINT).
# Not the model version date shown in the deployment.
AI_API_VERSION="2024-12-01-preview"

# AI filter: a yes/no question the model is asked about each message
AI_FILTER="please response yes or no if text contains wish to buy rubles (RUB) in exchange of dinars (RSD)"
```

### `my_account.session`: Telegram login

`my_account.session` is Pyrogram's saved login for your account. With it, the app doesn't need to log in again on each start. Treat it like a password: anyone who has this file has full access to your account.

To create it, run the app once on your computer:

```bash
pip install -r requirements.txt
python main.py
```

Log in when it asks: enter your phone number, then the code Telegram sends you, then your 2FA password if you have one. `my_account.session` then appears in the project folder. Stop the app with Ctrl+C. From now on the app starts without asking, locally and in Docker.

### The bot

1. In Telegram, open [@BotFather](https://t.me/BotFather), send `/newbot` and follow the steps. It gives you a token: put it in `.env` as `BOT_TOKEN`.
2. Add the bot to the `MY_DESTINATION` channel as an admin with the right to post messages. Without that, sending fails.

The bot doesn't need a login: on first start the app creates `mygrep_bot.session` from the token by itself, locally and in Docker. The bot only sends; it doesn't read the watched chats (your account does that).

## How it works

```
new message in a watched chat
  → preliminary filter   (local, free)
  → AI filter            (Azure OpenAI, costs tokens)
  → bot reposts to MY_DESTINATION (split into several messages if longer than 4096 characters)
```

### Filters

- **Preliminary filter** (`preliminary_text_filter.py`, `PRELIMINARY_FILTER`)
  - **Purpose:** saves money. It is a quick local check that rejects obviously unrelated messages, so they never reach the AI.
  - **Syntax:** quoted substrings combined with `and` / `or` / `not` and parentheses, e.g. `("buy" or "sell") and "RSD" and not "spam"`.
  - **Matching:** not case-sensitive.
  - **Special values:** `TRUE` passes every message to the AI; `FALSE` passes none.
- **AI filter** (`ai_text_filter.py`, `AI_FILTER`)
  - **Purpose:** makes the actual decision. The model is asked the `AI_FILTER` question about the message, and the message is reposted only if it answers "yes".
  - **Errors:** if the AI call fails (timeout, rate limit, etc.), the message is skipped.

### Files

| File | Purpose |
|---|---|
| `main.py` | Two Pyrogram clients: your account receives messages and runs the filters; the bot sends the repost of each match (source link + author + original formatting) |
| `html_splitter.py` | Splits a long HTML repost into chunks within Telegram's 4096-character limit; tags are closed and reopened at chunk borders, so every chunk is valid HTML |
| `text_filter.py` | Reads the filter settings from `.env` and chains the two filters: preliminary first, AI only if it passed |
| `preliminary_text_filter.py` | Parses the `PRELIMINARY_FILTER` expression safely (with `ast`, never executed) |
| `ai_text_filter.py` | Asks the model the yes/no question |
| `config.py` | Loads `.env`; on a bad setting, stops at startup with a clear message |
| `tests/` | Unit tests with fake settings. `test_manual.py` uses your real `.env` and calls the real AI, so it costs tokens |

## Run

**Locally:**

```bash
python main.py
```

**In Docker.** Both files are copied into the image, so build it only after they exist:

```bash
docker build -t mytggrep .
docker run -d --restart unless-stopped --name mytggrep mytggrep
```

**Tests:**

```bash
pip install -r requirements-dev.txt
pytest --ignore=tests/test_manual.py
```
