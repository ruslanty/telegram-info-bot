from unittest.mock import AsyncMock

import pytest
from aiogram.types import WebhookInfo

from telegram_info_bot.config import ConfigError, Settings
from telegram_info_bot.webhook import manage_webhook

TOKEN = "123456789:" + "a" * 35
SECRET = "b" * 64


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://user:pass@example.com",
        "https://example.com/path",
        "https://example.com?token=x",
        "https://example.com:bad",
    ],
)
def test_register_rejects_invalid_origin(url):
    with pytest.raises(ConfigError):
        Settings(TOKEN, SECRET, url).webhook_url()


async def test_register_preserves_pending_updates():
    bot = AsyncMock()
    bot.set_webhook.return_value = True
    settings = Settings(TOKEN, SECRET, "https://example.ngrok.app/")
    assert await manage_webhook("register", settings, bot) == {"registered": True}
    bot.set_webhook.assert_awaited_once_with(
        url="https://example.ngrok.app/telegram/webhook",
        secret_token=SECRET,
        allowed_updates=["message"],
        drop_pending_updates=False,
    )


async def test_delete_preserves_pending_updates():
    bot = AsyncMock()
    await manage_webhook("delete", Settings(TOKEN, SECRET), bot)
    bot.delete_webhook.assert_awaited_once_with(drop_pending_updates=False)


async def test_info_only_reports_safe_fields():
    bot = AsyncMock()
    bot.get_webhook_info.return_value = WebhookInfo(
        url="https://secret.example",
        has_custom_certificate=False,
        pending_update_count=2,
        last_error_message="private user info",
    )
    result = await manage_webhook("info", Settings(TOKEN, SECRET), bot)
    assert result == {"registered": True, "pending_update_count": 2, "has_delivery_error": True}


def test_cli_configuration_error_does_not_expose_secrets(monkeypatch, capsys):
    from telegram_info_bot.webhook import main

    monkeypatch.setattr("sys.argv", ["webhook", "register"])
    monkeypatch.setenv("BOT_TOKEN", TOKEN)
    monkeypatch.setenv("WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("WEBHOOK_BASE_URL", "http://bad")
    assert main() == 2
    output = capsys.readouterr()
    assert TOKEN not in output.err
    assert SECRET not in output.err
    assert "Traceback" not in output.err
