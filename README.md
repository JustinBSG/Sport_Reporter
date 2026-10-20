# Sport Reporter Discord bot

A small Python 3.11+ Discord bot to verify connectivity and preview sports
notifications before connecting the backend.

- `/ping` replies privately with a health check.
- `/sample` posts a fictional League of Legends match embed in the current channel.
  Its start time is 30 minutes after invocation, displayed in each viewer's local time.

## Create a Discord bot

1. Create an application in the [Discord Developer Portal](https://discord.com/developers/applications).
2. Open **Bot**, create/reset the bot token, and save it locally as `DISCORD_TOKEN`.
3. Under **OAuth2 > URL Generator**, select `bot` and `applications.commands`.
   Grant **View Channels**, **Send Messages**, and **Embed Links**, then use the
   generated URL to install the bot in a server you manage.
4. For quick development, enable Discord's Developer Mode, copy the server ID,
   and set `DISCORD_GUILD_ID`. Leave it blank for global registration instead.

The bot uses default intents; privileged Message Content, Members, and Presence
intents are unnecessary for these slash commands.

## Run locally (PowerShell)

Run these commands from this worktree's project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and fill in your bot token and optional server ID.
.\.venv\Scripts\python.exe bot.py
```

Environment variables take precedence over `.env`. The bot loads `.env` beside
`bot.py`, even if started from another directory. Keep the token private; `.env`
and virtual environments are ignored by Git.

Wait for the online log, then run `/ping` and `/sample` in your server. Guild
commands appear quickly; global commands can take time to propagate. Commands
are synced at login. Keep `DISCORD_GUILD_ID` consistent during development to
avoid registering both guild and global copies. Stop the bot with Ctrl+C.

This sample has no live match fetching, backend integration, or automatic alerts.
See the [discord.py slash command example](https://github.com/Rapptz/discord.py/blob/master/examples/app_commands/basic.py)
for the library's command registration pattern.
