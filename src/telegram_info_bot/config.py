from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from aiogram.utils.token import TokenValidationError, validate_token


class ConfigError(ValueError):
    """Configuration error safe to display without exposing environment values."""


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str = field(repr=False)
    webhook_secret: str = field(repr=False)
    webhook_base_url: str = ""
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        values = os.environ if env is None else env
        token = values.get("BOT_TOKEN", "")
        secret = values.get("WEBHOOK_SECRET", "")
        try:
            validate_token(token)
        except TokenValidationError:
            raise ConfigError("BOT_TOKEN is missing or invalid") from None
        if not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", secret):
            raise ConfigError("WEBHOOK_SECRET must contain 32–256 ASCII letters, digits, _ or -")
        level = values.get("LOG_LEVEL", "INFO").upper()
        if level not in {"INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ConfigError("LOG_LEVEL must be INFO, WARNING, ERROR or CRITICAL")
        return cls(token, secret, values.get("WEBHOOK_BASE_URL", ""), level)

    def webhook_url(self) -> str:
        try:
            url = urlsplit(self.webhook_base_url)
            valid = (
                url.scheme == "https"
                and bool(url.hostname)
                and url.username is None
                and url.password is None
                and url.path in {"", "/"}
                and not url.query
                and not url.fragment
                and url.port in {None, 443, 80, 88, 8443}
            )
        except ValueError:
            valid = False
        if not valid:
            raise ConfigError(
                "WEBHOOK_BASE_URL must be an HTTPS origin without credentials or path"
            )
        return self.webhook_base_url.rstrip("/") + "/telegram/webhook"
