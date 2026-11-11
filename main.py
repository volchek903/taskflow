from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from aiohttp import web

from bot.app import TaskflowBot
from bot.config import Settings
from bot.db import Database
from bot.server import create_app

ROOT = Path(__file__).resolve().parent


async def run() -> None:
    settings = Settings.from_env()
    database = Database(settings.database_path)
    await database.initialize()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    frontend_dir = ROOT / "frontend" / "dist"
    if not (frontend_dir / "index.html").is_file():
        raise RuntimeError("frontend/dist is missing; build the frontend first")

    runner = web.AppRunner(create_app(frontend_dir, settings, database))
    await runner.setup()
    site = web.TCPSite(runner, settings.host, settings.port)
    await site.start()
    logging.getLogger(__name__).info(
        "Taskflow frontend is listening on http://%s:%s", settings.host, settings.port
    )

    try:
        await TaskflowBot(settings, database).run()
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
