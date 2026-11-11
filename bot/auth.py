from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import parse_qsl

from aiohttp import web

from .config import Settings
from .db import Database


def verify_init_data(value: str, bot_token: str, max_age: int = 86400) -> dict[str, Any]:
    fields = dict(parse_qsl(value, keep_blank_values=True))
    received_hash = fields.pop("hash", "")
    fields.pop("signature", None)
    if not received_hash:
        raise ValueError("Telegram signature is missing")
    check_string = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise ValueError("Invalid Telegram signature")
    auth_date = int(fields.get("auth_date", "0"))
    age = time.time() - auth_date
    if auth_date <= 0 or age < -30 or age > max_age:
        raise ValueError("Telegram authorization has expired")
    user = json.loads(fields.get("user", "{}"))
    if not isinstance(user, dict) or not user.get("id"):
        raise ValueError("Telegram user is missing")
    return user


async def authenticate(request: web.Request) -> int:
    settings: Settings = request.app["settings"]
    database: Database = request.app["database"]
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    try:
        if init_data:
            profile = verify_init_data(init_data, settings.bot_token)
        elif settings.allow_dev_auth:
            telegram_id = int(request.headers.get("X-Taskflow-Dev-User", "900000001"))
            profile = {"id": telegram_id, "first_name": "Локальный", "last_name": "Пользователь", "username": f"dev_{telegram_id}"}
        else:
            raise ValueError("Open Taskflow from Telegram")
        return await database.upsert_user(profile)
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        raise web.HTTPUnauthorized(text=json.dumps({"error": str(error)}, ensure_ascii=False), content_type="application/json") from error
