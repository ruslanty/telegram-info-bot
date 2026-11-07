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
def test_help_lists_only_available_commands(resources, command, chat_type):
    app, session = resources
    with TestClient(app) as client:
        assert send(client, command, chat_type=chat_type).status_code == 200
    method = session.make_request.call_args.args[1]
    lines = method.text.splitlines()
    assert lines[0] == "Commands:"
    assert [line.split(" - ")[0] for line in lines[1:]] == [
        "/start",
        "/me",
        "/chat",
        "/help",
        "/privacy",
    ]
    assert all(len(line) < 50 for line in lines[1:])
    assert method.parse_mode is None


@pytest.mark.parametrize("command", ["/privacy", "/privacy@test_bot"])
def test_privacy_is_short_and_neutral(resources, command):
    app, session = resources
    with TestClient(app) as client:
        assert send(client, command).status_code == 200
    text = session.make_request.call_args.args[1].text
    assert text == (
        "Your profile and chat details are used to reply to your commands. "
        "The bot does not save them."
    )


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
        ("/privacy", "Your profile and chat details"),
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
