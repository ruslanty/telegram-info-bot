import logging

from telegram_info_bot.logging_config import configure_logging


def test_log_level_applies_when_host_already_configured_logging():
    root = logging.getLogger()
    logger = logging.getLogger("telegram_info_bot")
    previous_level = logger.level
    handler = logging.NullHandler()
    root.addHandler(handler)
    try:
        configure_logging("ERROR")
        assert not logger.isEnabledFor(logging.WARNING)
        assert logger.isEnabledFor(logging.ERROR)
        assert not logging.getLogger("telegram_info_bot.http.routes").isEnabledFor(logging.WARNING)
    finally:
        logger.setLevel(previous_level)
        root.removeHandler(handler)
