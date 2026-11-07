from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from fastapi import FastAPI

from telegram_info_bot.config import Settings
from telegram_info_bot.http.routes import router
from telegram_info_bot.logging_config import configure_logging
from telegram_info_bot.telegram.router import create_router


def create_app(settings: Settings | None = None, *, bot: Bot | None = None) -> FastAPI:
    config = settings if settings is not None else Settings.from_env()
    configure_logging(config.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        client = (
            bot if bot is not None else Bot(config.bot_token, session=AiohttpSession(timeout=10))
        )
        dispatcher = Dispatcher(disable_fsm=True)
        dispatcher.include_router(create_router())
        app.state.bot = client
        app.state.dispatcher = dispatcher
        try:
            await dispatcher.emit_startup(bot=client)
            app.state.ready = True
            yield
        finally:
            app.state.ready = False
            try:
                await dispatcher.emit_shutdown(bot=client)
            finally:
                await client.session.close()

    app = FastAPI(title="Telegram Info Bot", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.settings = config
    app.state.ready = False
    app.include_router(router)
    return app
