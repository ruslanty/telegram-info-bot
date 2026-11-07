import pytest
from fastapi.testclient import TestClient

TOKEN = "123456789:" + "a" * 35
SECRET = "b" * 64
HEADERS = {"X-Telegram-Bot-Api-Secret-Token": SECRET}


def send(client, text, language="en", chat_type="private"):
    message = {
        "message_id": 1,
        "date": 1,
        "chat": {"id": 42, "type": chat_type},
        "from": {"id": 42, "is_bot": False, "first_name": "User", "language_code": language},
    }
    if text is not None:
        message["text"] = text
        if text.startswith("/"):
            message["entities"] = [
                {"type": "bot_command", "offset": 0, "length": len(text.split()[0])}
            ]
    else:
        message["sticker"] = {
            "file_id": "x",
            "file_unique_id": "y",
            "type": "regular",
            "width": 10,
            "height": 10,
            "is_animated": False,
            "is_video": False,
        }
    return client.post(
        "/telegram/webhook", json={"update_id": 1, "message": message}, headers=HEADERS
    )


@pytest.mark.parametrize("command", ["/help", "/help@test_bot"])
@pytest.mark.parametrize("chat_type", ["private", "supergroup"])
def test_help_lists_commands_and_explains_ids(resources, command, chat_type):
    app, session = resources
    with TestClient(app) as client:
        assert send(client, command, chat_type=chat_type).status_code == 200
    method = session.make_request.call_args.args[1]
    assert all(
        command in method.text for command in ["/start", "/me", "/chat", "/help", "/privacy"]
    )
    assert "/chat@test_bot" in method.text
    assert "A user ID identifies your account" in method.text
    assert method.parse_mode is None


@pytest.mark.parametrize("command", ["/privacy", "/privacy@test_bot"])
def test_privacy_describes_actual_processing(resources, command):
    app, session = resources
    with TestClient(app) as client:
        assert send(client, command).status_code == 200
    text = session.make_request.call_args.args[1].text
    assert "does not store" in text
    assert "Telegram" in text and "ngrok" in text
    assert "participants" in text
    assert "<" not in text


@pytest.mark.parametrize(
    "text", ["/unknown", "hello <script>", "/unknown@test_bot\nargument", "   "]
)
def test_private_fallback_does_not_echo_input(resources, text):
    app, session = resources
    with TestClient(app) as client:
        assert send(client, text).status_code == 200
    method = session.make_request.call_args.args[1]
    assert "/help" in method.text
    assert text not in method.text
    assert "Use /help" in method.text


@pytest.mark.parametrize("text", ["hello", "/unknown", None])
def test_groups_do_not_receive_fallback(resources, text):
    app, session = resources
    with TestClient(app) as client:
        assert send(client, text, chat_type="supergroup").status_code == 200
    session.make_request.assert_not_called()


@pytest.mark.parametrize("command", ["/help@other_bot", "/unknown@other_bot"])
def test_private_fallback_ignores_commands_for_other_bots(resources, command):
    app, session = resources
    with TestClient(app) as client:
        assert send(client, command).status_code == 200
    session.make_request.assert_not_called()


@pytest.mark.parametrize("language", ["ru", "de", None])
@pytest.mark.parametrize(
    "command,expected",
    [
        ("/start", "Your Telegram ID"),
        ("/me", "First name:"),
        ("/chat", "Type:"),
        ("/help", "Commands:"),
        ("/privacy", "Data handling"),
    ],
)
def test_all_commands_use_english_regardless_of_profile_language(
    resources, language, command, expected
):
    app, session = resources
    with TestClient(app) as client:
        assert send(client, command, language).status_code == 200
    method = session.make_request.call_args.args[1]
    assert expected in method.text
    if method.reply_markup:
        assert method.reply_markup.inline_keyboard[0][0].text == "Copy ID"
