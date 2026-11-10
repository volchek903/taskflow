from __future__ import annotations

from pathlib import Path

from aiohttp import web


def create_app(frontend_dir: Path) -> web.Application:
    app = web.Application()
    index_file = frontend_dir / "index.html"
    assets_dir = frontend_dir / "assets"

    async def health(_: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    async def spa(request: web.Request) -> web.StreamResponse:
        requested = (frontend_dir / request.match_info["path"]).resolve()
        try:
            requested.relative_to(frontend_dir.resolve())
        except ValueError:
            raise web.HTTPNotFound() from None
        if requested.is_file():
            return web.FileResponse(requested)
        return web.FileResponse(index_file)

    app.router.add_get("/health", health)
    if assets_dir.is_dir():
        app.router.add_static("/assets", assets_dir, append_version=False)
    app.router.add_get("/{path:.*}", spa)
    return app
