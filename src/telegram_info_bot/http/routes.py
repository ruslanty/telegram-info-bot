import asyncio
import json
import logging
import secrets

from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiogram.types import Update
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

router = APIRouter()
logger = logging.getLogger(__name__)
MAX_BODY_BYTES = 1024 * 1024
BODY_TIMEOUT_SECONDS = 5
PROCESSING_TIMEOUT_SECONDS = 15


@router.get("/")
async def index() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(request: Request) -> JSONResponse:
    initialized = request.app.state.ready
    return JSONResponse(
        {"status": "ready" if initialized else "not_ready"}, status_code=200 if initialized else 503
    )


@router.post("/telegram/webhook")
async def webhook(request: Request) -> JSONResponse:
    config = request.app.state.settings
    supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not secrets.compare_digest(supplied.encode(), config.webhook_secret.encode()):
        return JSONResponse({"detail": "Forbidden"}, status_code=403)
    if not request.app.state.ready:
        return JSONResponse({"detail": "Not ready"}, status_code=503)
    body = bytearray()
    try:
        async with asyncio.timeout(BODY_TIMEOUT_SECONDS):
            async for chunk in request.stream():
                if len(body) + len(chunk) > MAX_BODY_BYTES:
                    return JSONResponse({"detail": "Request too large"}, status_code=413)
                body.extend(chunk)
    except TimeoutError:
        logger.warning("webhook_body_timeout")
        return JSONResponse({"detail": "Request timed out"}, status_code=408)
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeDecodeError, RecursionError):
        return JSONResponse({"detail": "Invalid JSON"}, status_code=400)
    try:
        update = Update.model_validate(payload)
    except ValidationError:
        return JSONResponse({"detail": "Invalid update"}, status_code=422)
    if update.message is None:
        return JSONResponse({"ok": True})
    try:
        async with asyncio.timeout(PROCESSING_TIMEOUT_SECONDS):
            await request.app.state.dispatcher.feed_update(request.app.state.bot, update)
    except (TelegramForbiddenError, TelegramBadRequest):
        logger.warning("telegram_delivery_rejected")
    except TelegramRetryAfter as error:
        logger.warning("telegram_rate_limited")
        return JSONResponse(
            {"detail": "Temporarily unavailable"},
            status_code=503,
            headers={"Retry-After": str(max(1, error.retry_after))},
        )
    except (TelegramNetworkError, TelegramServerError):
        logger.warning("telegram_temporarily_unavailable")
        return JSONResponse({"detail": "Temporarily unavailable"}, status_code=503)
    except TimeoutError:
        logger.warning("webhook_processing_timeout")
        return JSONResponse({"detail": "Temporarily unavailable"}, status_code=503)
    except Exception as error:
        # Never include exception text/traceback: Telegram errors may contain user data.
        logger.error("webhook_processing_failed error_type=%s", type(error).__name__)
        return JSONResponse({"detail": "Temporarily unavailable"}, status_code=503)
    return JSONResponse({"ok": True})
