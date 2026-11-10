from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import aiohttp

from .api import TelegramAPI, TelegramAPIError
from .config import Settings

logger = logging.getLogger(__name__)
WIDGET_HTML = (Path(__file__).with_name("widget.html")).read_text(encoding="utf-8")


class TaskflowBot:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.offset: int | None = None

    async def run(self) -> None:
        async with TelegramAPI(self.settings.bot_token, self.settings.bot_api_base) as api:
            await api.call("deleteWebhook", drop_pending_updates=False)
            me = await api.call("getMe")
            await api.call(
                "setMyCommands",
                commands=[{"command": "start", "description": "Открыть Taskflow"}],
            )
            logger.info("Bot @%s started with Bot API 10.4 widgets", me.get("username"))
            while True:
                try:
                    await self._poll(api)
                except asyncio.CancelledError:
                    raise
                except (aiohttp.ClientError, asyncio.TimeoutError, TelegramAPIError):
                    logger.exception("Polling failed; retrying in 3 seconds")
                    await asyncio.sleep(3)

    async def _poll(self, api: TelegramAPI) -> None:
        payload: dict[str, Any] = {
            "timeout": 50,
            "allowed_updates": ["message"],
        }
        if self.offset is not None:
            payload["offset"] = self.offset
        updates = await api.call("getUpdates", **payload)
        for update in updates:
            self.offset = update["update_id"] + 1
            await self._handle_update(api, update)

    async def _handle_update(self, api: TelegramAPI, update: dict[str, Any]) -> None:
        message = update.get("message")
        if not message:
            return
        text = message.get("text", "")
        command = text.split(maxsplit=1)[0].split("@", 1)[0].lower()
        if command != "/start":
            return

        chat = message.get("chat", {})
        chat_id = chat.get("id")
        if chat_id is None:
            return
        if chat.get("type") != "private":
            await api.call(
                "sendMessage",
                chat_id=chat_id,
                text="Widget доступен в личном чате со мной. Откройте бота и отправьте /start.",
            )
            return

        keyboard = {
            "inline_keyboard": [[{
                "text": "Открыть Taskflow",
                "style": "primary",
                "web_app": {"url": self.settings.webapp_url},
            }]]
        }
        try:
            await api.call(
                "sendWidget",
                chat_id=chat_id,
                html=WIDGET_HTML,
                height=396,
                caption="Taskflow — задачи и проекты в одном месте",
                reply_markup=keyboard,
            )
        except TelegramAPIError:
            logger.exception("sendWidget failed; sending a Mini App button fallback")
            await api.call(
                "sendMessage",
                chat_id=chat_id,
                text="Откройте Taskflow:",
                reply_markup=keyboard,
            )
