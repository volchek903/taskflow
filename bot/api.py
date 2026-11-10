from __future__ import annotations

from typing import Any

import aiohttp


class TelegramAPIError(RuntimeError):
    pass


class TelegramAPI:
    def __init__(self, token: str, base_url: str) -> None:
        self._url = f"{base_url}/bot{token}"
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "TelegramAPI":
        timeout = aiohttp.ClientTimeout(total=70, connect=10)
        self._session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._session is not None:
            await self._session.close()

    async def call(self, method: str, **payload: Any) -> Any:
        if self._session is None:
            raise RuntimeError("TelegramAPI must be used as an async context manager")
        async with self._session.post(f"{self._url}/{method}", json=payload) as response:
            try:
                body = await response.json()
            except (aiohttp.ContentTypeError, ValueError) as error:
                raise TelegramAPIError(
                    f"Telegram {method} returned HTTP {response.status} with invalid JSON"
                ) from error
        if not response.ok or not body.get("ok"):
            description = body.get("description", f"HTTP {response.status}")
            raise TelegramAPIError(f"Telegram {method}: {description}")
        return body.get("result")
