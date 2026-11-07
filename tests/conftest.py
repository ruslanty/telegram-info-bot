from unittest.mock import AsyncMock

import pytest
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import Message, User

from telegram_info_bot.app import create_app
from telegram_info_bot.config import Settings


@pytest.fixture
def resources():
    session = AiohttpSession()
    session.make_request = AsyncMock(
        return_value=Message.model_validate(
            {
                "message_id": 2,
                "date": 1,
                "chat": {"id": 42, "type": "private"},
                "text": "ok",
            }
        )
    )
    session.close = AsyncMock()
    bot = Bot("123456789:" + "a" * 35, session=session)
    bot._me = User(id=123456789, is_bot=True, first_name="Test", username="test_bot")
    return create_app(Settings(bot.token, "b" * 64), bot=bot), session
