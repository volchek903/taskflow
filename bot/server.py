from __future__ import annotations

from pathlib import Path
import logging
import asyncio
from typing import Any, Awaitable, Callable

from aiohttp import web
import aiohttp

from .auth import authenticate
from .api import TelegramAPI, TelegramAPIError
from .config import Settings
from .db import Database

logger = logging.getLogger(__name__)


@web.middleware
async def api_errors(request: web.Request, handler: Callable[[web.Request], Awaitable[web.StreamResponse]]) -> web.StreamResponse:
    try:
        return await handler(request)
    except web.HTTPException:
        raise
    except PermissionError as error:
        return web.json_response({"error": str(error)}, status=403)
    except LookupError as error:
        return web.json_response({"error": str(error)}, status=404)
    except (ValueError, TypeError) as error:
        return web.json_response({"error": str(error)}, status=400)


async def json_body(request: web.Request) -> dict[str, Any]:
    try:
        value = await request.json()
    except Exception as error:
        raise ValueError("Ожидался JSON-запрос") from error
    if not isinstance(value, dict):
        raise ValueError("Ожидался JSON-объект")
    return value


def create_app(frontend_dir: Path, settings: Settings, database: Database) -> web.Application:
    app = web.Application(middlewares=[api_errors])
    app["settings"] = settings
    app["database"] = database
    index_file = frontend_dir / "index.html"
    assets_dir = frontend_dir / "assets"

    async def health(_: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    async def bootstrap(request: web.Request) -> web.Response:
        user_id = await authenticate(request)
        return web.json_response(await database.bootstrap(user_id))

    async def create_project(request: web.Request) -> web.Response:
        user_id = await authenticate(request); payload = await json_body(request)
        name = str(payload.get("name", "")).strip()
        if not name: raise ValueError("Укажите название проекта")
        project_id = await database.create_project(user_id, name)
        return web.json_response({"id": project_id}, status=201)

    async def update_project(request: web.Request) -> web.Response:
        user_id = await authenticate(request); payload = await json_body(request)
        project_id = request.match_info["project_id"]
        if "statuses" in payload:
            await database.set_statuses(user_id, project_id, payload["statuses"], payload.get("renames"))
        elif "joinEnabled" in payload:
            await database.set_join_enabled(user_id, project_id, bool(payload["joinEnabled"]))
        else:
            raise ValueError("Не указаны настройки проекта")
        return web.json_response({"ok": True})

    async def create_invite(request: web.Request) -> web.Response:
        user_id = await authenticate(request); payload = await json_body(request)
        identifier = str(payload.get("identifier") or "").strip() or None
        invite = await database.create_invite(user_id, request.match_info["project_id"], identifier, payload.get("role", "member"))
        invite["url"] = (f"https://t.me/{settings.bot_username}?start=join_{invite['code']}"
                         if settings.bot_username else f"{settings.webapp_url}/#/join/{invite['code']}")
        telegram_id = invite.pop("telegramId", None)
        if telegram_id:
            try:
                async with TelegramAPI(settings.bot_token, settings.bot_api_base) as api:
                    await api.call("sendMessage", chat_id=int(telegram_id),
                                   text=f"Вас приглашают в проект «{invite['projectName']}» в Taskflow.",
                                   reply_markup={"inline_keyboard": [[{"text": "Открыть приглашение", "url": invite["url"]}]]})
            except (TelegramAPIError, aiohttp.ClientError, asyncio.TimeoutError):
                logger.exception("Could not deliver project invitation to Telegram user %s", telegram_id)
        return web.json_response(invite, status=201)

    async def join_invite(request: web.Request) -> web.Response:
        user_id = await authenticate(request); payload = await json_body(request)
        code = str(payload.get("code", "")).strip()
        if not code: raise ValueError("Введите код приглашения")
        project_id = await database.join_invite(user_id, code)
        return web.json_response({"projectId": project_id})

    async def set_member(request: web.Request) -> web.Response:
        user_id = await authenticate(request); payload = await json_body(request)
        await database.set_member(user_id, request.match_info["project_id"], str(payload.get("identifier", "")), payload.get("role", "member"))
        return web.json_response({"ok": True})

    async def preview_invite(request: web.Request) -> web.Response:
        user_id = await authenticate(request)
        return web.json_response(await database.preview_invite(user_id, request.match_info["code"]))

    async def decline_invite(request: web.Request) -> web.Response:
        user_id = await authenticate(request); payload = await json_body(request)
        await database.decline_invite(user_id, str(payload.get("code", "")))
        return web.json_response({"ok": True})

    async def create_task(request: web.Request) -> web.Response:
        user_id = await authenticate(request); payload = await json_body(request)
        if not str(payload.get("title", "")).strip(): raise ValueError("Укажите название задачи")
        task_id = await database.create_task(user_id, payload)
        return web.json_response({"id": task_id}, status=201)

    async def update_task(request: web.Request) -> web.Response:
        user_id = await authenticate(request); payload = await json_body(request)
        await database.update_task(user_id, request.match_info["task_id"], payload)
        return web.json_response({"ok": True})

    async def reorder_tasks(request: web.Request) -> web.Response:
        user_id = await authenticate(request); payload = await json_body(request)
        tasks = payload.get("tasks")
        if not isinstance(tasks, list): raise ValueError("Список задач не передан")
        await database.reorder_tasks(user_id, tasks)
        return web.json_response({"ok": True})

    async def spa(request: web.Request) -> web.StreamResponse:
        requested = (frontend_dir / request.match_info["path"]).resolve()
        try:
            requested.relative_to(frontend_dir.resolve())
        except ValueError:
            raise web.HTTPNotFound() from None
        if requested.is_file(): return web.FileResponse(requested)
        return web.FileResponse(index_file)

    app.router.add_get("/health", health)
    app.router.add_get("/api/bootstrap", bootstrap)
    app.router.add_post("/api/projects", create_project)
    app.router.add_patch("/api/projects/{project_id}", update_project)
    app.router.add_post("/api/projects/{project_id}/invites", create_invite)
    app.router.add_post("/api/projects/{project_id}/members", set_member)
    app.router.add_get("/api/invites/{code}", preview_invite)
    app.router.add_post("/api/invites/decline", decline_invite)
    app.router.add_post("/api/invites/join", join_invite)
    app.router.add_post("/api/tasks", create_task)
    app.router.add_patch("/api/tasks/{task_id}", update_task)
    app.router.add_post("/api/tasks/reorder", reorder_tasks)
    if assets_dir.is_dir(): app.router.add_static("/assets", assets_dir, append_version=False)
    app.router.add_get("/{path:.*}", spa)
    return app
