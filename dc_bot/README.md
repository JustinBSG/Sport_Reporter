# Sport Reporter Discord bot

The bot uses Python 3.15 or later. It provides four slash commands:

| Command | Action |
| --- | --- |
| `/ping` | Check the bot connection with a private reply |
| `/sample` | Show a fictional match without a backend request |
| `/upcoming hours:24 leagues:lck,nba` | Get upcoming matches from the backend |
| `/results hours:24 leagues:worlds` | Get completed matches with recent updates |

The API commands return private replies with a maximum of ten embeds. An embed
is a Discord message panel with match fields. Demo records have a clear label.

The bot does not collect live sports data or send scheduled alerts. These features
require more development.

Brand assets: [App icon](assets/sport-reporter-icon.png) and
[profile banner](assets/sport-reporter-banner.png).

## Deploy to Railway

Use the [Railway setup guide](../docs/railway-setup.md) for the complete procedure.
The guide includes the Discord application, bot installation, backend, and
PostgreSQL setup.

1. Create a service named `discord-bot` from this repository.
2. Set its root directory to `/dc_bot`.
3. Use the Dockerfile in this directory.
4. If the API service is named `backend`, add these variables:

   ```dotenv
   DISCORD_TOKEN=your-discord-bot-token
   DISCORD_GUILD_ID=your-test-server-id
   BACKEND_URL=http://${{backend.RAILWAY_PRIVATE_DOMAIN}}:8000
   SPORT_REPORTER_API_KEY=${{backend.SPORT_REPORTER_API_KEY}}
   ```

5. Set the replica count to `1`.
6. Disable app sleeping.
7. Leave public networking, HTTP healthcheck, and cron schedule empty.
8. Leave custom build, start, and pre-deploy commands empty.

The Dockerfile uses Python 3.15 and the dependencies in `uv.lock`. It starts
`python bot.py`. The bot connects to Discord and does not need an inbound port.
Do not give the bot database credentials.

## Create the Discord application

1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
2. Create an application.
3. Get its **Bot token**.
4. Select the installation scopes `bot` and `applications.commands`.
5. Grant **View Channels**, **Send Messages**, and **Embed Links**.
6. Install the bot in your server.
7. Leave privileged intents disabled.
8. Leave **Interactions Endpoint URL** blank.

The bot receives commands through the Discord Gateway connection.

For development:

1. Enable Developer Mode in Discord.
2. Copy your test server ID.
3. Set `DISCORD_GUILD_ID` to this ID.

To register global commands, leave `DISCORD_GUILD_ID` blank. Global commands can
take time to appear. A change between server and global registration can leave
old commands. Keep the development setting consistent. Remove old registrations
when you change the setting.

## Run locally with PowerShell

Install [uv](https://docs.astral.sh/uv/) before you start.

1. Open PowerShell in the `dc_bot` directory.
2. Install the dependencies:

   ```powershell
   uv sync --locked --extra dev
   ```

3. Create `.env` if the file does not exist:

   ```powershell
   if (-not (Test-Path .env)) { Copy-Item .env.example .env }
   ```

4. Open the configuration file:

   ```powershell
   notepad .env
   ```

5. Set `DISCORD_TOKEN` to your bot token.
6. If you use a test server, set `DISCORD_GUILD_ID` to its ID.
7. For API commands, set `BACKEND_URL` to the backend origin, such as `http://127.0.0.1:8000`.
8. Set `SPORT_REPORTER_API_KEY` to the exact key that the backend uses.
9. Save `.env`.
10. Stop other bot processes that use the same token.
11. Start the bot:

    ```powershell
    uv run python bot.py
    ```

The backend origin includes the scheme, hostname, and optional port. Do not add
`/docs` or another path. If you leave both API variables blank, `/ping` and
`/sample` work without the backend. API commands then return a configuration
message.

Process environment variables take priority over `.env` values. The bot reads
the `.env` file beside `bot.py`. Never commit this file. Use a separate development
bot token if the hosted bot must continue to run.

## Run tests

Run this command from the `dc_bot` directory:

```powershell
uv run pytest -q
```

The tests check HTTP authentication, filters, backend errors, and demo labels.
They do not connect to Discord or send messages.
