# Architecture

```text
Telegram → FastAPI webhook → aiogram handler → Telegram reply
```

The code lives in `src/telegram_info_bot`. `app.py` creates the application and closes its resources at shutdown. `http/routes.py` validates webhook requests and passes updates to aiogram. `telegram/router.py` handles commands.

Handlers pass user and chat data to the formatters, which escape values for Telegram HTML. `telegram/texts.py` holds help and privacy text; `telegram/keyboards.py` builds copy buttons. The webhook management CLI is in `webhook.py`.

| Module | Responsibility |
|---|---|
| `app.py` | Creates the app and manages resource lifetime |
| `http/routes.py` | Webhook validation, health checks, HTTP responses |
| `telegram/router.py` | Telegram commands |
| `telegram/models.py` | User and chat data |
| `telegram/formatting.py` | Escaped message formatting |
| `telegram/keyboards.py` | Copy-ID buttons |
| `telegram/texts.py` | Help and privacy text |
| `config.py` | Environment settings |
| `logging_config.py` | Logging setup |
| `webhook.py` | Webhook management CLI |
