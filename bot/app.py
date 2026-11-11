from __future__ import annotations

import asyncio
import html
import logging
from pathlib import Path
from typing import Any
from urllib.parse import quote

import aiohttp

from .api import TelegramAPI, TelegramAPIError
from .config import Settings
from .db import Database

logger = logging.getLogger(__name__)
WIDGET_HTML = (Path(__file__).with_name("widget.html")).read_text(encoding="utf-8")


class TaskflowBot:
    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database
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
        # Telegram messages are not guaranteed to contain text (stickers,
        # photos, service messages, and empty/whitespace-only payloads). Only
        # parse a command when a non-empty text token is actually present.
        text = message.get("text")
        if not isinstance(text, str):
            return
        parts = text.split(maxsplit=1)
        if not parts:
            return
        command = parts[0].split("@", 1)[0].lower()
        if command != "/start":
            return
        start_parameter = parts[1].strip() if len(parts) > 1 else ""
        join_code = start_parameter[5:] if start_parameter.startswith("join_") else ""

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

        sender = message.get("from") or {}
        if sender.get("id"):
            await self.database.upsert_user(sender)
        summary = await self.database.widget_summary(int(sender.get("id", chat_id)))
        tasks = summary["tasks"]
        done = sum(bool(task["done"]) for task in tasks)
        rows = "".join(
            f'<div class="task"><span class="check {"done" if task["done"] else ""}"></span>'
            f'<span class="name {"done" if task["done"] else ""}">{html.escape(task["title"])}</span>'
            f'<span class="time">{html.escape(task["time"] or task["project_name"])}</span></div>'
            for task in tasks
        ) or '<div class="empty">Назначенных задач пока нет</div>'
        widget_html = (WIDGET_HTML.replace("{{USER_NAME}}", html.escape(summary["name"]))
                       .replace("{{DONE}}", str(done)).replace("{{TOTAL}}", str(len(tasks)))
                       .replace("{{PROJECTS}}", str(summary["project_count"]))
                       .replace("{{PROGRESS}}", str(round(done / len(tasks) * 100) if tasks else 0))
                       .replace("{{TASKS}}", rows))

        mini_app_url = (f"{self.settings.webapp_url}/#/join/{quote(join_code)}"
                        if join_code else self.settings.webapp_url)
        keyboard = {
            "inline_keyboard": [[{
                "text": "Открыть Taskflow",
                "style": "primary",
                "web_app": {"url": mini_app_url},
            }]]
        }
        try:
            await api.call(
                "sendWidget",
                chat_id=chat_id,
                html=widget_html,
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
