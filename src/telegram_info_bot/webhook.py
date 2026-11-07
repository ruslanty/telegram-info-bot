import argparse
import asyncio
import json
import sys

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from dotenv import load_dotenv

from telegram_info_bot.config import ConfigError, Settings
from telegram_info_bot.logging_config import configure_logging


async def manage_webhook(command: str, settings: Settings, bot: Bot) -> dict[str, object]:
    if command == "register":
        registered = await bot.set_webhook(
            url=settings.webhook_url(),
            secret_token=settings.webhook_secret,
            allowed_updates=["message"],
            drop_pending_updates=False,
        )
        return {"registered": registered}
    if command == "delete":
        return {"deleted": await bot.delete_webhook(drop_pending_updates=False)}
    info = await bot.get_webhook_info()
    return {
        "registered": bool(info.url),
        "pending_update_count": info.pending_update_count,
        "has_delivery_error": bool(info.last_error_message),
    }


async def run(command: str, settings: Settings) -> dict[str, object]:
    if command == "register":
        settings.webhook_url()  # Validate before opening a network session.
    async with Bot(settings.bot_token, session=AiohttpSession(timeout=10)) as bot:
        return await manage_webhook(command, settings, bot)


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage the Telegram webhook explicitly")
    parser.add_argument("command", choices=("register", "info", "delete"))
    args = parser.parse_args()
    load_dotenv(".env", override=False)
    try:
        settings = Settings.from_env()
        configure_logging(settings.log_level)
        result = asyncio.run(run(args.command, settings))
    except ConfigError as error:
        print(str(error), file=sys.stderr)
        return 2
    except Exception:
        print(
            "Telegram request failed; check credentials, network and webhook configuration.",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
