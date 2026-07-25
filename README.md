# Shopping List Telegram Bot

Family shopping list Telegram bot for adding, listing, clearing, and undoing shopping items. It is allowed to contain Russian user-facing examples because the household workflow is Russian-first.

## Features

- Manages a shared shopping list through Telegram commands.
- Supports list, clear, undo, help, and start flows.
- Keeps user-facing examples practical for Russian-speaking household use.

## Architecture

- **Repository:** `MilaArtyNew/shopping-list-bot`
- **Primary stack:** Python, Railway
- **Entrypoints and scripts:**
  - `main.py`
- **Notable dependencies:** `SpeechRecognition`, `imageio-ffmpeg`, `openai`, `pydub`, `python-dotenv`, `python-telegram-bot`

## Configuration

Configure the service with environment variables. Do not commit real secrets to the repository.

- `BOT_TOKEN` — required or optional runtime configuration. See deployment environment for the actual value.
- `GEMINI_API_KEY` — required or optional runtime configuration. See deployment environment for the actual value.
- `TELEGRAM_BOT_TOKEN` — required or optional runtime configuration. See deployment environment for the actual value.
- `TELEGRAM_TOKEN` — required or optional runtime configuration. See deployment environment for the actual value.

## Setup

```bash
git clone https://github.com/MilaArtyNew/shopping-list-bot
cd shopping-list-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running Locally

```bash
python main.py
```

## Bot Commands

- `/clear` — Clear the current list.
- `/help` — Show help and available commands.
- `/list` — List tracked items.
- `/start` — Start the bot and show the main entry message.
- `/undo` — Undo the last action.

If a command requires extra input and the argument is missing, the bot should ask a follow-up question instead of failing silently.

## Deployment Notes

- Keep secrets in the deployment platform environment variables, not in Git.
- Use the default branch as the source of truth for deployments.
- Check logs after every deployment and verify the `/status` or health endpoint when available.
- If the project uses a scheduler, verify timezone assumptions and idempotency before enabling it in production.

## Operational Notes

- Review logs after startup for missing environment variables or API authentication errors.
- Keep command names in English and document every user-facing command in this README.
- For Telegram bots, `/help` should list the same commands documented here.
- Inline buttons should edit the original message with the final status rather than sending duplicate messages.

## Troubleshooting

- **Bot does not respond:** verify the bot token, webhook/polling mode, and chat permissions.
- **Missing data:** check API keys, rate limits, and upstream service status.
- **Deployment starts but exits:** inspect platform logs for missing environment variables or import errors.
- **Commands differ from README:** update the command list here and in the bot command menu at the same time.

## Security

- Never commit `.env` files, API keys, private keys, Telegram tokens, or session strings.
- Use `.env.example` for placeholders only.
- Rotate any credential that was accidentally committed.
