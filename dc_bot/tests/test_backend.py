import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest

from backend_client import BackendClient
from bot import Config, SportReporterBot, match_embed


def test_client_passes_auth_filters_and_aware_timestamp():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=[])

    async def scenario():
        client = BackendClient("http://backend.railway.internal:8000", "secret", httpx.MockTransport(handler))
        try:
            await client.upcoming(12, "lck,nba")
            await client.results(datetime(2026, 1, 1, tzinfo=timezone.utc), None)
        finally:
            await client.close()

    asyncio.run(scenario())
    assert requests[0].headers["authorization"] == "Bearer secret"
    assert requests[0].url.path == "/upcoming"
    assert requests[0].url.params["leagues"] == "lck,nba"
    assert requests[1].url.params["since"].endswith("+00:00")


def test_client_rejects_http_errors_and_invalid_response():
    async def scenario():
        for response, exception in [(httpx.Response(401), httpx.HTTPStatusError),
                                    (httpx.Response(200, json={"error": "bad"}), ValueError)]:
            client = BackendClient("http://backend", "secret", httpx.MockTransport(lambda _: response))
            try:
                with pytest.raises(exception):
                    await client.upcoming(24, None)
            finally:
                await client.close()
    asyncio.run(scenario())


def test_demo_embed_identifies_fictional_data():
    embed = match_embed({
        "team1": {"name": "Demo Blue", "score": 3},
        "team2": {"name": "Demo Red", "score": 1},
        "start_time_utc": "2026-01-01T12:00:00Z", "sport": "lol", "league": "worlds",
        "status": "completed", "best_of": 5, "is_demo": True,
    })
    assert "Fictional" in embed.description
    assert "Demo only" in embed.footer.text
    assert any(field.value == "3 - 1" for field in embed.fields)


def test_bot_handles_backend_auth_failure_after_deferring():
    async def scenario():
        bot = SportReporterBot(Config("unused", None, "http://backend", "secret"))
        request = httpx.Request("GET", "http://backend/upcoming")
        response = httpx.Response(401, request=request)
        backend = AsyncMock()
        backend.upcoming.side_effect = httpx.HTTPStatusError("unauthorized", request=request, response=response)
        bot.backend = backend
        interaction = AsyncMock()
        await bot.show_matches(interaction, "upcoming", 24, None)
        interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
        assert "authentication failed" in interaction.followup.send.call_args.args[0]
        await bot.close()
    asyncio.run(scenario())
