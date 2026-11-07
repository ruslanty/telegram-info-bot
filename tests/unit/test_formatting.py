from telegram_info_bot.telegram.formatting import format_user_info
from telegram_info_bot.telegram.models import UserInfo


def test_optional_fields_are_omitted_and_values_are_escaped():
    text = format_user_info(UserInfo(42, '<Test & "name">'))
    assert "<code>42</code>" in text
    assert "&lt;Test &amp; &quot;name&quot;&gt;" in text
    assert "Username:" not in text
    assert "Language:" not in text
    assert "Last name:" not in text
    assert "None" not in text


def test_all_fields():
    text = format_user_info(UserInfo(42, "Test", "User", "test_user", "ru"))
    assert "First name: Test" in text
    assert "Last name: User" in text
    assert "Username: @test_user" in text
    assert "Language: ru" in text


def test_chat_formatting_omits_missing_title_and_uses_english():
    from telegram_info_bot.telegram.formatting import format_chat_info
    from telegram_info_bot.telegram.models import ChatInfo

    text = format_chat_info(ChatInfo(-100123, "supergroup"))
    assert text == "Chat ID: <code>-100123</code>\nType: supergroup"
