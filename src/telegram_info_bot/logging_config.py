import logging


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("telegram_info_bot").setLevel(level)
    # Framework event logs contain user IDs; exception messages can contain payloads.
    for name in ("aiogram", "aiohttp", "httpx", "httpcore"):
        logging.getLogger(name).disabled = True
    for name in ("aiogram.event", "aiogram.dispatcher", "aiogram.middlewares"):
        logging.getLogger(name).disabled = True
