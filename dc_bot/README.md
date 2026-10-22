# Sport Reporter Discord bot

Brand assets: [App icon](assets/sport-reporter-icon.png) and
[Discord profile banner](assets/sport-reporter-banner.png).

A Python 3.15+ Discord bot with four slash commands:

- `/ping`: private bot connectivity check.
- `/sample`: fictional embed generated locally, without calling the backend.
- `/upcoming hours:24 leagues:lck,nba`: read upcoming matches from the backend.
- `/results hours:24 leagues:worlds`: read recently updated completed matches.

The API commands return private replies with at most ten embeds. Fictional rows
are clearly marked as demo data. Live extraction and automatic scheduled alerts
are separate features that are not implemented yet.

## Deploy to Railway

Follow the [complete Railway tutorial](../docs/railway-setup.md), including the
Discord application/invite setup and PostgreSQL/backend deployment.
Deploy this folder as a continuously running `discord-bot` service, root directory
`/dc_bot`. Its Dockerfile uses Python 3.15 and `uv.lock`.

Railway variables, assuming the API service is named `backend`:

```dotenv
DISCORD_TOKEN=your-discord-bot-token
DISCORD_GUILD_ID=your-test-server-id
BACKEND_URL=http://${{backend.RAILWAY_PRIVATE_DOMAIN}}:8000
SPORT_REPORTER_API_KEY=${{backend.SPORT_REPORTER_API_KEY}}
```

Use one replica, disable sleeping, and leave public networking, HTTP healthcheck,
cron schedule, and custom start/pre-deploy commands empty. The Dockerfile starts
`python bot.py`. The bot needs outbound Discord connectivity, not an inbound port.
Do not give the bot database credentials.

## Discord application

Create an application in the [Developer Portal](https://discord.com/developers/applications),
get its **Bot token**, and install it with scopes `bot` and `applications.commands`.
Grant View Channels, Send Messages, and Embed Links. Privileged intents are not
required. Leave Interactions Endpoint URL blank because this bot uses the Gateway.

For development, copy your server ID using Discord Developer Mode and set
`DISCORD_GUILD_ID`. Leave it blank for global commands when appropriate; global
registration can take time. Switching scopes can leave old command registrations,
so keep the development scope consistent and clean up old registrations deliberately.

## Local development (PowerShell)

From this folder, with [uv](https://docs.astral.sh/uv/) installed:

```powershell
uv sync --locked --extra dev
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
uv run python bot.py
```

Set your token and optional server ID. For API commands, set `BACKEND_URL` to the
backend origin (locally `http://127.0.0.1:8000`) and use its exact API key.
The URL must not include `/docs` or another path. Leaving both API variables blank
allows only the standalone connectivity/sample functionality.

Environment variables take precedence over `.env`. The bot loads `.env` beside
`bot.py`; never commit it. Stop any Railway or VM process using the same token
before running locally, or use a different development bot token.

## Tests

```powershell
uv run pytest -q
```

The tests verify HTTP authorization/filtering, backend failures, and demo labels
without logging in to Discord or sending messages.
