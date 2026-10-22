"""Authenticated, asynchronous API access; the bot never receives DB credentials."""

from datetime import datetime

import httpx


class BackendClient:
    def __init__(self, base_url: str, api_key: str, transport=None):
        self.client = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(10, connect=5),
            transport=transport,
            trust_env=False,
        )

    async def matches(self, route: str, params: dict) -> list[dict]:
        response = await self.client.get(route, params=params)
        response.raise_for_status()
        matches = response.json()
        if not isinstance(matches, list) or not all(isinstance(m, dict) for m in matches):
            raise ValueError("Backend returned an invalid match list")
        return matches

    async def upcoming(self, hours: int, leagues: str | None) -> list[dict]:
        params = {"hours": hours}
        if leagues:
            params["leagues"] = leagues
        return await self.matches("upcoming", params)

    async def results(self, since: datetime, leagues: str | None) -> list[dict]:
        params = {"since": since.isoformat()}
        if leagues:
            params["leagues"] = leagues
        return await self.matches("results", params)

    async def close(self) -> None:
        await self.client.aclose()
