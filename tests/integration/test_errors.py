import asyncio
from unittest.mock import AsyncMock

import pytest
from aiogram import Dispatcher
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiogram.methods import SendMessage
from fastapi.testclient import TestClient

TOKEN = "123456789:" + "a" * 35
SECRET = "b" * 64
HEADERS = {"X-Telegram-Bot-Api-Secret-Token": SECRET}
UPDATE = {
    "update_id": 1,
    "message": {
        "message_id": 1,
        "date": 1,
        "chat": {"id": 42, "type": "private"},
        "from": {"id": 42, "is_bot": False, "first_name": "PRIVATE_NAME"},
        "text": "/start",
        "entities": [{"type": "bot_command", "offset": 0, "length": 6}],
    },
}
METHOD = SendMessage(chat_id=42, text="private payload")


@pytest.mark.parametrize(
    "error,status,event",
    [
        (TelegramRetryAfter(METHOD, TOKEN + SECRET, retry_after=600), 503, "telegram_rate_limited"),
        (TelegramNetworkError(METHOD, TOKEN + SECRET), 503, "telegram_temporarily_unavailable"),
        (TelegramServerError(METHOD, TOKEN + SECRET), 503, "telegram_temporarily_unavailable"),
        (TelegramBadRequest(METHOD, TOKEN + SECRET), 200, "telegram_delivery_rejected"),
        (RuntimeError(TOKEN + SECRET), 503, "webhook_processing_failed"),
    ],
)
def test_error_is_bounded_safe_and_next_request_recovers(resources, error, status, event, caplog):
    app, session = resources
    reply = session.make_request.return_value
    session.make_request.side_effect = [error, reply]
    with TestClient(app) as client:
        result = client.post("/telegram/webhook", json=UPDATE, headers=HEADERS)
        assert result.status_code == status
        if isinstance(error, TelegramRetryAfter):
            assert result.headers["retry-after"] == "600"
        assert client.post("/telegram/webhook", json=UPDATE, headers=HEADERS).status_code == 200
    assert session.make_request.await_count == 2
    assert event in caplog.text
    for private in (TOKEN, SECRET, "PRIVATE_NAME", "private payload"):
        assert private not in caplog.text + result.text


def test_processing_timeout_cancels_outbound_request(resources, monkeypatch, caplog):
    from telegram_info_bot.http import routes

    app, session = resources
    cancelled = []

    async def slow_request(*args, **kwargs):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(True)

    session.make_request.side_effect = slow_request
    monkeypatch.setattr(routes, "PROCESSING_TIMEOUT_SECONDS", 0.01)
    with TestClient(app) as client:
        result = client.post("/telegram/webhook", json=UPDATE, headers=HEADERS)
        assert result.status_code == 503
        assert client.get("/health/ready").status_code == 200
    assert cancelled == [True]
    assert "webhook_processing_timeout" in caplog.text
    session.close.assert_awaited_once()


@pytest.mark.parametrize("hook", ["emit_startup", "emit_shutdown"])
def test_lifecycle_failure_still_closes_session(resources, monkeypatch, hook):
    app, session = resources
    monkeypatch.setattr(Dispatcher, hook, AsyncMock(side_effect=RuntimeError("hook failed")))
    with pytest.raises(RuntimeError, match="hook failed"), TestClient(app):
        pass
    assert app.state.ready is False
    session.close.assert_awaited_once()


async def test_cancellation_propagates_and_closes_resources(resources):
    app, session = resources
    with pytest.raises(asyncio.CancelledError):
        async with app.router.lifespan_context(app):
            assert app.state.ready is True
            raise asyncio.CancelledError
    assert app.state.ready is False
    session.close.assert_awaited_once()


def test_unexpected_error_logs_type_but_not_message(resources, caplog):
    app, session = resources
    session.make_request.side_effect = ValueError(TOKEN + SECRET + " PRIVATE_NAME")
    with TestClient(app) as client:
        response = client.post("/telegram/webhook", json=UPDATE, headers=HEADERS)
    assert response.status_code == 503
    record = next(r for r in caplog.records if r.message.startswith("webhook_processing_failed"))
    assert "error_type=ValueError" in record.message
    assert record.exc_info is None
    for value in (TOKEN, SECRET, "PRIVATE_NAME"):
        assert value not in caplog.text + response.text


async def test_slow_body_times_out_without_dispatching(resources, monkeypatch):
    from types import SimpleNamespace

    from telegram_info_bot.http import routes

    app, session = resources
    cancelled = []

    async def slow_body():
        yield b"{"
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(True)

    request = SimpleNamespace(app=app, headers=HEADERS, stream=slow_body)
    monkeypatch.setattr(routes, "BODY_TIMEOUT_SECONDS", 0.01)
    async with app.router.lifespan_context(app):
        response = await asyncio.wait_for(routes.webhook(request), timeout=1)
        assert response.status_code == 408
        assert app.state.ready is True
    assert cancelled == [True]
    session.make_request.assert_not_called()
    session.close.assert_awaited_once()
