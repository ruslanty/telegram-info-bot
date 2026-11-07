from copy import deepcopy
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import Message, User
from fastapi.testclient import TestClient

from telegram_info_bot.app import create_app
from telegram_info_bot.config import Settings

TOKEN = "123456789:" + "a" * 35
SECRET = "b" * 64
HEADERS = {"X-Telegram-Bot-Api-Secret-Token": SECRET}


@pytest.mark.parametrize(
    "chat_type,chat_id,title",
    [
        ("private", 42, None),
        ("group", -123, "<Group & friends>"),
        ("supergroup", -1001234567890, "<Group & friends>"),
        ("group", -123, None),
    ],
)
@pytest.mark.parametrize("command", ["/chat", "/chat@test_bot"])
def test_chat_uses_current_chat_and_exact_copy_value(chat_type, chat_id, title, command):
    session = AiohttpSession()
    session.make_request = AsyncMock(
        return_value=Message.model_validate(
            {"message_id": 2, "date": 1, "chat": {"id": chat_id, "type": chat_type}}
        )
    )
    session.close = AsyncMock()
    bot = Bot(TOKEN, session=session)
    bot._me = User(id=123456789, is_bot=True, first_name="Test", username="test_bot")
    chat = {"id": chat_id, "type": chat_type}
    if title:
        chat["title"] = title
    update = {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "date": 1,
            "chat": chat,
            "from": {"id": 99, "is_bot": False, "first_name": "User", "language_code": "ru"},
            "text": command,
            "entities": [{"type": "bot_command", "offset": 0, "length": len(command)}],
        },
    }
    with TestClient(create_app(Settings(TOKEN, SECRET), bot=bot)) as client:
        assert client.post("/telegram/webhook", json=update, headers=HEADERS).status_code == 200
    method = session.make_request.call_args.args[1]
    assert method.chat_id == chat_id
    assert f"<code>{chat_id}</code>" in method.text
    assert f"Type: {chat_type}" in method.text
    assert ("Title:" in method.text) is bool(title)
    if title:
        assert "&lt;Group &amp; friends&gt;" in method.text
    assert method.parse_mode == "HTML"
    assert method.reply_markup.inline_keyboard[0][0].copy_text.text == str(chat_id)


@pytest.mark.parametrize(
    "sender", [None, {"id": 1087968824, "is_bot": True, "first_name": "Anonymous"}]
)
def test_chat_works_for_anonymous_admin_without_user_language(sender):
    session = AiohttpSession()
    session.make_request = AsyncMock(
        return_value=Message.model_validate(
            {"message_id": 2, "date": 1, "chat": {"id": -100123, "type": "supergroup"}}
        )
    )
    session.close = AsyncMock()
    update = {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "date": 1,
            "chat": {"id": -100123, "type": "supergroup", "title": "Group"},
            "sender_chat": {"id": -100999, "type": "supergroup", "title": "Sender"},
            "text": "/chat",
            "entities": [{"type": "bot_command", "offset": 0, "length": 5}],
        },
    }
    if sender:
        update["message"]["from"] = deepcopy(sender)
    bot = Bot(TOKEN, session=session)
    with TestClient(create_app(Settings(TOKEN, SECRET), bot=bot)) as client:
        assert client.post("/telegram/webhook", json=update, headers=HEADERS).status_code == 200
    method = session.make_request.call_args.args[1]
    assert "Type: supergroup" in method.text
    assert "<code>-100123</code>" in method.text
    assert "Sender" not in method.text
    assert method.reply_markup.inline_keyboard[0][0].text == "Copy ID"
