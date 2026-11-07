# Telegram Info Bot

Find your Telegram user ID or a group's chat ID and copy it with one tap. Built with Python, FastAPI, and aiogram.

## Commands

| Command | Description |
|---|---|
| `/start` | Get started |
| `/me` | Your ID and profile details |
| `/chat` | Chat ID, type, and title |
| `/help` | Usage examples |
| `/privacy` | How the bot handles data |

In groups, address commands to your bot: `/chat@example_info_bot`.

## Local setup

Install [uv](https://docs.astral.sh/uv/) and [ngrok](https://ngrok.com/). Create a bot with [BotFather](https://t.me/BotFather).

```sh
uv sync --locked
test -f .env || cp .env.example .env
chmod 600 .env
uv run python -c 'import secrets; print(secrets.token_hex(32))'
```

In `.env`, set `BOT_TOKEN` to the BotFather token and `WEBHOOK_SECRET` to the generated value.

Start the app:

```sh
uv run uvicorn telegram_info_bot.app:create_app --factory --env-file .env \
  --host 127.0.0.1 --port 8000 --timeout-graceful-shutdown 20
```

In another terminal:

```sh
ngrok http 8000 --inspect=false
```

Copy the ngrok HTTPS address into `WEBHOOK_BASE_URL` in `.env`, then register the webhook:

```sh
uv run python -m telegram_info_bot.webhook register
```

Send `/start` to your bot. If the ngrok address changes, update `WEBHOOK_BASE_URL` and register again.

Use `uv run python -m telegram_info_bot.webhook info` to check the webhook, or replace `info` with `delete` to remove it.

## Docker

```sh
docker build -t telegram-info-bot .
docker run --rm --name telegram-info-bot \
  --env-file .env --read-only --tmpfs /tmp \
  --cap-drop=ALL --security-opt=no-new-privileges \
  -p 127.0.0.1:8000:8000 telegram-info-bot
```

Keep values unquoted in the Docker env file. To stop the container:

```sh
docker stop --time 25 telegram-info-bot
```

## Development

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv audit --locked
uv build
python3 scripts/check_container.py telegram-info-bot
```

See [Architecture](docs/architecture.md) for the request flow and module boundaries.

[MIT License](LICENSE)
