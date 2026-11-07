import pytest

from telegram_info_bot.config import ConfigError, Settings

TOKEN = "123456789:" + "a" * 35
SECRET = "b" * 64


def test_settings_hide_secrets():
    settings = Settings.from_env({"BOT_TOKEN": TOKEN, "WEBHOOK_SECRET": SECRET})
    assert TOKEN not in repr(settings)
    assert SECRET not in repr(settings)


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"BOT_TOKEN": "bad", "WEBHOOK_SECRET": SECRET},
        {"BOT_TOKEN": TOKEN, "WEBHOOK_SECRET": "short"},
        {"BOT_TOKEN": TOKEN, "WEBHOOK_SECRET": "☃" * 64},
        {"BOT_TOKEN": TOKEN, "WEBHOOK_SECRET": SECRET, "LOG_LEVEL": "BAD"},
    ],
)
def test_invalid_config_is_safe(values):
    with pytest.raises(ConfigError) as error:
        Settings.from_env(values)
    assert TOKEN not in str(error.value)
    assert SECRET not in str(error.value)
