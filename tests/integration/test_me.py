from copy import deepcopy

import pytest
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
        "from": {"id": 42, "is_bot": False, "first_name": "<Test>", "language_code": "ru"},
        "text": "/me",
        "entities": [{"type": "bot_command", "offset": 0, "length": 3}],
    },
}


@pytest.mark.parametrize("command", ["/me", "/me@test_bot"])
def test_me_shows_command_sender_and_copy_button(resources, command):
    app, session = resources
    update = deepcopy(UPDATE)
    update["message"]["text"] = command
    update["message"]["entities"][0]["length"] = len(command)
    update["message"]["reply_to_message"] = {
        "message_id": 9,
        "date": 1,
        "chat": {"id": 42, "type": "private"},
        "from": {"id": 99, "is_bot": False, "first_name": "Other"},
    }
    with TestClient(app) as client:
        assert client.post("/telegram/webhook", json=update, headers=HEADERS).status_code == 200
    method = session.make_request.call_args.args[1]
    assert "<code>42</code>" in method.text
    assert "&lt;Test&gt;" in method.text
    assert "Other" not in method.text
    assert method.parse_mode == "HTML"
    button = method.reply_markup.inline_keyboard[0][0]
    assert button.copy_text.text == "42"
    assert button.text == "Copy ID"


@pytest.mark.parametrize("anonymous", ["sender_chat", "missing_from"])
def test_anonymous_sender_gets_explanation_without_copy_button(resources, anonymous):
    app, session = resources
    update = deepcopy(UPDATE)
    if anonymous == "sender_chat":
        update["message"]["sender_chat"] = {"id": -100123, "type": "supergroup", "title": "Group"}
    else:
        del update["message"]["from"]
    with TestClient(app) as client:
        assert client.post("/telegram/webhook", json=update, headers=HEADERS).status_code == 200
    method = session.make_request.call_args.args[1]
    assert "<code>42</code>" not in method.text
    assert method.reply_markup is None
    assert "Send /me in a private chat" in method.text


def test_group_response_shows_profile_without_extra_explanations(resources):
    app, session = resources
    update = deepcopy(UPDATE)
    update["message"]["chat"] = {"id": -100123, "type": "supergroup", "title": "Group"}
    with TestClient(app) as client:
        assert client.post("/telegram/webhook", json=update, headers=HEADERS).status_code == 200
    method = session.make_request.call_args.args[1]
    assert method.text == "ID: <code>42</code>\nFirst name: &lt;Test&gt;\nLanguage: ru"
    assert method.reply_markup.inline_keyboard[0][0].copy_text.text == "42"
