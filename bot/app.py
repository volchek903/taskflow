from __future__ import annotations

import asyncio
import html
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import aiohttp

from .api import TelegramAPI, TelegramAPIError
from .config import Settings
from .db import Database

logger = logging.getLogger(__name__)
WIDGET_HTML = (Path(__file__).with_name("widget.html")).read_text(encoding="utf-8")
COMMANDS = {
    "/start": ("Сегодня", "/today"),
    "/today": ("Сегодня", "/today"),
    "/projects": ("Проекты", "/projects"),
    "/inbox": ("Входящие", "/inbox"),
    "/settings": ("Профиль", "/settings"),
}


def _initials(user: dict[str, Any]) -> str:
    return ((user.get("firstName") or "?")[:1] + (user.get("lastName") or "")[:1]).upper()


def render_widget(command: str, state: dict[str, Any]) -> str:
    user = state["user"]
    title = ""
    subtitle = ""
    extra = ""
    rows: list[str] = []

    if command in {"/start", "/today"}:
        today = datetime.now().date().isoformat()
        tasks = [task for task in state["tasks"] if not task["due"] or task["due"] <= today]
        done = sum(bool(task["done"]) for task in tasks)
        title = f"{user['firstName']}, задачи на сегодня"
        subtitle = f"{done} из {len(tasks)} выполнено"
        progress = round(done / len(tasks) * 100) if tasks else 0
        extra = f'<div class="progress"><i style="width:{progress}%"></i></div>'
        projects = {project["id"]: project["name"] for project in state["projects"]}
        for task in tasks[:4]:
            task_title = html.escape(task["title"])
            project = html.escape(projects.get(task["project"], "Без проекта"))
            time = html.escape(task["time"] or "")
            done_class = " done" if task["done"] else ""
            rows.append(f'<div class="item"><span class="marker{done_class}">{"✓" if task["done"] else ""}</span><span class="content"><span class="name{done_class}">{task_title}</span><span class="meta">{project}</span></span><span class="value">{time}</span></div>')
    elif command == "/projects":
        projects = state["projects"]
        title = "Ваши проекты"
        subtitle = f"{len(projects)} проектов · совместная работа"
        for project in projects[:4]:
            task_count = sum(task["project"] == project["id"] for task in state["tasks"])
            avatars = "".join(f'<span class="avatar">{html.escape(_initials(member))}</span>' for member in project["members"][:4])
            rows.append(f'<div class="item"><span class="marker">P</span><span class="content"><span class="name">{html.escape(project["name"])}</span><span class="meta">{task_count} задач</span></span><span class="avatars">{avatars}</span><span class="value">{project["memberCount"]}</span></div>')
    elif command == "/inbox":
        notices = state["notices"]
        title = "Входящие"
        subtitle = f"{len(notices)} новых приглашений"
        for notice in notices[:4]:
            rows.append(f'<div class="item"><span class="marker">→</span><span class="content"><span class="name">{html.escape(notice["title"])}</span><span class="meta">{html.escape(notice["text"])}</span></span></div>')
    else:
        title = user["name"]
        username = f"@{user['username']}" if user.get("username") else f"Telegram ID {user['telegramId']}"
        subtitle = html.escape(username)
        rows = [
            f'<div class="item"><span class="marker">P</span><span class="content"><span class="name">Проекты</span><span class="meta">Доступные рабочие пространства</span></span><span class="value">{len(state["projects"])}</span></div>',
            f'<div class="item"><span class="marker">T</span><span class="content"><span class="name">Задачи</span><span class="meta">Все задачи в ваших проектах</span></span><span class="value">{len(state["tasks"])}</span></div>',
            f'<div class="item"><span class="marker">{html.escape(_initials(user))}</span><span class="content"><span class="name">Telegram-профиль подключён</span><span class="meta">Данные синхронизируются через SQLite</span></span></div>',
        ]

    body = "".join(rows) or '<div class="empty">Здесь пока ничего нет</div>'
    section = COMMANDS.get(command, COMMANDS["/start"])[0]
    return (WIDGET_HTML.replace("{{SECTION}}", html.escape(section))
            .replace("{{TITLE}}", html.escape(title)).replace("{{SUBTITLE}}", subtitle)
            .replace("{{EXTRA}}", extra).replace("{{BODY}}", body))


class TaskflowBot:
    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database
        self.offset: int | None = None

    async def run(self) -> None:
        async with TelegramAPI(self.settings.bot_token, self.settings.bot_api_base) as api:
            await api.call("deleteWebhook", drop_pending_updates=False)
            me = await api.call("getMe")
            await api.call("setMyCommands", commands=[
                {"command": "start", "description": "Открыть Taskflow"},
                {"command": "today", "description": "Задачи на сегодня"},
                {"command": "projects", "description": "Мои проекты"},
                {"command": "inbox", "description": "Входящие приглашения"},
                {"command": "settings", "description": "Профиль и настройки"},
            ])
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
        payload: dict[str, Any] = {"timeout": 50, "allowed_updates": ["message"]}
        if self.offset is not None:
            payload["offset"] = self.offset
        updates = await api.call("getUpdates", **payload)
        for update in updates:
            self.offset = update["update_id"] + 1
            await self._handle_update(api, update)

    async def _handle_update(self, api: TelegramAPI, update: dict[str, Any]) -> None:
        message = update.get("message")
        if not message or not isinstance(message.get("text"), str):
            return
        parts = message["text"].split(maxsplit=1)
        if not parts:
            return
        command = parts[0].split("@", 1)[0].lower()
        if command not in COMMANDS:
            return
        start_parameter = parts[1].strip() if command == "/start" and len(parts) > 1 else ""
        join_code = start_parameter[5:] if start_parameter.startswith("join_") else ""
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        if chat_id is None:
            return
        if chat.get("type") != "private":
            await api.call("sendMessage", chat_id=chat_id, text="Виджеты Taskflow доступны в личном чате с ботом.")
            return

        sender = message.get("from") or {}
        if not sender.get("id"):
            return
        user_id = await self.database.upsert_user(sender)
        state = await self.database.bootstrap(user_id)
        widget_html = render_widget(command, state)
        route = f"/join/{quote(join_code)}" if join_code else COMMANDS[command][1]
        mini_app_url = f"{self.settings.webapp_url}/#{route}"
        label = COMMANDS[command][0]
        keyboard = {"inline_keyboard": [[{"text": f"Открыть: {label}", "style": "primary", "web_app": {"url": mini_app_url}}]]}
        try:
            await api.call("sendWidget", chat_id=chat_id, html=widget_html, height=396,
                           caption=f"Taskflow · {label}", reply_markup=keyboard)
        except TelegramAPIError:
            logger.exception("sendWidget failed; sending a Mini App button fallback")
            await api.call("sendMessage", chat_id=chat_id, text=f"Taskflow · {label}", reply_markup=keyboard)
