from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    webapp_url: str
    host: str
    port: int
    log_level: str
    bot_api_base: str
    database_path: str
    allow_dev_auth: bool
    bot_username: str

    @classmethod
    def from_env(cls) -> "Settings":
        bot_token = os.getenv("BOT_TOKEN", "").strip()
        webapp_url = os.getenv("WEBAPP_URL", "").strip().rstrip("/")
        if not bot_token:
            raise RuntimeError("BOT_TOKEN is required")
        parsed = urlparse(webapp_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise RuntimeError("WEBAPP_URL must be a public HTTPS URL")

        try:
            port = int(os.getenv("PORT", "8080"))
        except ValueError as error:
            raise RuntimeError("PORT must be an integer") from error

        return cls(
            bot_token=bot_token,
            webapp_url=webapp_url,
            host=os.getenv("HOST", "0.0.0.0"),
            port=port,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            bot_api_base=os.getenv("BOT_API_BASE", "https://api.telegram.org").rstrip("/"),
            database_path=os.getenv("DATABASE_PATH", "/data/taskflow.db"),
            allow_dev_auth=os.getenv("ALLOW_DEV_AUTH", "false").lower() in {"1", "true", "yes"},
            bot_username=os.getenv("BOT_USERNAME", "").strip().lstrip("@"),
        )
