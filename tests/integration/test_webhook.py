import pytest
from aiogram.exceptions import TelegramForbiddenError, TelegramNetworkError
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
        "from": {"id": 42, "is_bot": False, "first_name": "Test", "language_code": "ru"},
        "text": "/start",
        "entities": [{"type": "bot_command", "offset": 0, "length": 6}],
    },
}


def test_start_and_lifecycle(resources):
    app, session = resources
    with TestClient(app) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 200
        response = client.post("/telegram/webhook", json=UPDATE, headers=HEADERS)
        assert response.status_code == 200
        method = session.make_request.call_args.args[1]
        assert isinstance(method, SendMessage)
        assert "42" in method.text
        assert "/me" in method.text
    session.close.assert_awaited_once()
    assert app.state.ready is False


@pytest.mark.parametrize("secret", [None, "wrong", "☃" * 32])
def test_secret_is_checked_before_body(resources, secret):
    app, session = resources
    # Non-ASCII values cannot be represented by HTTPX's default header encoding.
    headers = {} if secret is None else {"X-Telegram-Bot-Api-Secret-Token": secret.encode()}
    with TestClient(app) as client:
        result = client.post("/telegram/webhook", content=b"not json", headers=headers)
        assert result.status_code == 403
    session.make_request.assert_not_called()


@pytest.mark.parametrize("body,status", [(b"not json", 400), (b'{"private":"secret"}', 422)])
def test_validation_does_not_echo_payload(resources, body, status):
    app, session = resources
    with TestClient(app) as client:
        response = client.post("/telegram/webhook", content=body, headers=HEADERS)
        assert response.status_code == status
        assert "private" not in response.text
        assert "secret" not in response.text
    session.make_request.assert_not_called()


def test_ignored_update_and_repeated_delivery(resources):
    app, session = resources
    with TestClient(app) as client:
        assert (
            client.post("/telegram/webhook", json={"update_id": 3}, headers=HEADERS).status_code
            == 200
        )
        for _ in range(2):
            assert client.post("/telegram/webhook", json=UPDATE, headers=HEADERS).status_code == 200
    assert session.make_request.await_count == 2


@pytest.mark.parametrize(
    "error,status",
    [
        (TelegramForbiddenError(method=SendMessage(chat_id=42, text="x"), message="private"), 200),
        (TelegramNetworkError(method=SendMessage(chat_id=42, text="x"), message="private"), 503),
        (RuntimeError("private"), 503),
    ],
)
def test_delivery_errors_are_safe(resources, error, status, caplog):
    app, session = resources
    session.make_request.side_effect = error
    with TestClient(app) as client:
        response = client.post("/telegram/webhook", json=UPDATE, headers=HEADERS)
        assert response.status_code == status
        assert "private" not in response.text
    assert "private" not in caplog.text


def test_readiness_before_startup(resources):
    app, _ = resources
    client = TestClient(app)
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 503


def test_body_limit(resources):
    app, _ = resources
    with TestClient(app) as client:
        result = client.post("/telegram/webhook", content=b"x" * (1024 * 1024 + 1), headers=HEADERS)
        assert result.status_code == 413


@pytest.mark.parametrize("chat_type,expected_id", [("private", True), ("group", False)])
def test_start_group_privacy(resources, chat_type, expected_id):
    from copy import deepcopy

    app, session = resources
    update = deepcopy(UPDATE)
    update["message"]["chat"]["type"] = chat_type
    with TestClient(app) as client:
        assert client.post("/telegram/webhook", json=update, headers=HEADERS).status_code == 200
    text = session.make_request.call_args.args[1].text
    assert ("42" in text) is expected_id
    assert ("Your Telegram ID" in text) is expected_id
