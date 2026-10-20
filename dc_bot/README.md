# Sport Reporter Discord bot

A small Python 3.15+ Discord bot to verify connectivity and preview sports
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

## Hosting decision: Oracle Cloud

The deployment target is Oracle Cloud Infrastructure (OCI). The bot runs on a
cloud VM and connects to Discord; it continues running when your computer is off.
GitHub remains the source repository.

The intended full system uses one Ubuntu ARM64 Ampere A1 VM with Docker Compose:

```text
Oracle Cloud VM
  Discord bot <-> FastAPI backend <-> PostgreSQL
                      ^                  ^
                      |                  |
                 Scheduled sports extractor

Discord <-> Discord bot
Sports APIs -> extractor
PostgreSQL -> backups stored outside the VM
```

| Component | Deployment plan |
| --- | --- |
| VM | Start with 2 OCPUs and 6 GB RAM; measure usage before resizing |
| Backend | Separate FastAPI container; internal API access for the bot |
| Discord bot | One continuously running container using Python 3.15 |
| Database | Self-managed PostgreSQL with a persistent data volume |
| Extractor | Separate scheduled worker for schedules and results |
| Recovery | Automatic service restarts, health checks, and tested database restores |

This VM size is an initial engineering estimate for personal use. One VM is a
single point of failure: maintenance or VM loss interrupts all services.
PostgreSQL should use persistent storage, preferably on a separately attached
block volume. Keep database port 5432 private. Add HTTPS access to the backend
when external clients need it. The Discord bot itself needs outbound HTTPS and
WebSocket access, with no public inbound application port.

### Cost and availability

Checked against Oracle documentation on 2026-10-21:

- The documented A1 free allowance is 1,500 OCPU-hours and 9,000 GB-hours monthly,
  equivalent to 2 OCPUs and 12 GB RAM continuously, shared across the tenancy.
- The documented free block-storage allowance is 200 GB combined boot/data volumes.
- Free compute must be created in the home region; available capacity can delay provisioning.
- Oracle may reclaim idle Always Free compute based on seven days of low CPU,
  network, and memory utilization. An online bot can still have low resource usage.

See [Oracle Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).
Check the actual tenancy limits and creation estimate before provisioning. Zero
infrastructure cost is possible within applicable allowances, but is not a
promise of uninterrupted availability. Plan paid capacity if interruptions are
unacceptable.

The initial database choice is PostgreSQL hosted on the VM. OCI managed
PostgreSQL is a paid option after trial credits, rather than an Always Free
service. Oracle Autonomous Database is a different database product and would
require different database integration. See the
[OCI service catalogue](https://www.oracle.com/cloud/free/).

### Deploy the current sample bot on OCI

The Compose architecture above is the target for the integrated system. This
branch currently contains the standalone sample bot; Dockerfiles, Compose
configuration, database integration, live extraction, and automatic notifications
are not implemented here. The following systemd setup runs the existing bot now.
When moving it into Compose, stop and disable this service first to avoid running
two copies.

1. Create an eligible Ubuntu ARM64 A1 VM in your OCI home region. Add your SSH
   public key. For this initial setup, use a public subnet, internet gateway,
   public IP, and outbound HTTPS access. Restrict inbound SSH to your admin IP
   using OCI networking rules and the host firewall. Do not open a bot HTTP port.
2. Push the desired `dc_bot` commits to GitHub before deploying. SSH into the VM
   as `ubuntu`. The commands and service paths below assume that account and
   `/home/ubuntu/Sport_Reporter`; change them together for another account/path.
3. Install Git and uv, then create the environment on the VM. If the repository
   is private, configure read access for Git before cloning.

```bash
sudo apt-get update
sudo apt-get install -y git curl ca-certificates
curl -LsSf https://astral.sh/uv/install.sh | sh

git clone --branch dc_bot https://github.com/JustinBSG/Sport_Reporter.git "$HOME/Sport_Reporter"
cd "$HOME/Sport_Reporter/dc_bot"
"$HOME/.local/bin/uv" python install 3.15
"$HOME/.local/bin/uv" sync --locked
install -m 600 .env.example .env
nano .env
```

Set `DISCORD_TOKEN` in `.env` to the real bot token. Set `DISCORD_GUILD_ID` to your
server ID for development registration, or leave it blank for global commands.
Create `.env` once during initial setup; do not overwrite it during updates.
Keep credentials on the VM or in an appropriate secrets store, outside Git.

uv creates a Linux environment using the Python 3.15 pin; do not copy a Windows
`.venv` to the VM. Installation must succeed on the selected ARM64 image before
enabling the service. See [uv installation](https://docs.astral.sh/uv/getting-started/installation/)
and [Python management](https://docs.astral.sh/uv/guides/install-python/).

4. Install the service so the bot starts at boot and restarts after a crash:

```bash
sudo tee /etc/systemd/system/sport-reporter-discord.service >/dev/null <<'EOF'
[Unit]
Description=Sport Reporter Discord bot
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Sport_Reporter/dc_bot
ExecStart=/home/ubuntu/Sport_Reporter/dc_bot/.venv/bin/python /home/ubuntu/Sport_Reporter/dc_bot/bot.py
Environment=PYTHONUNBUFFERED=1
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now sport-reporter-discord.service
sudo systemctl status sport-reporter-discord.service
sudo journalctl -u sport-reporter-discord.service -n 50 --no-pager
```

The bot loads `.env` beside `bot.py`. Look for the online log, then invoke `/ping`
and `/sample` in Discord. Disconnect SSH and repeat `/ping` to verify that the bot
is independent of the terminal. Also verify recovery after a planned VM reboot.
See [systemd service configuration](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html).

### Updates and operations

After pushing a bot update to GitHub, run on the VM:

```bash
sudo systemctl stop sport-reporter-discord.service
cd /home/ubuntu/Sport_Reporter
git pull --ff-only origin dc_bot
cd dc_bot
"$HOME/.local/bin/uv" sync --locked
sudo systemctl start sport-reporter-discord.service
sudo journalctl -u sport-reporter-discord.service -n 50 --no-pager
```

Run each step only after the previous one succeeds. If sync fails, resolve the
installation error before starting the service. Keep the previous deployed Git
commit and lockfile available for rollback. Repeat the slash-command checks after
updates, and stop any local bot process using the same token.

For the complete system, first integrate the backend and bot into a deployment
branch, then add the Compose services, PostgreSQL schema/migrations, extractor,
and persistent notification log. Store the backend API key separately from the
Discord token and pass it to the bot's future API client. Schedule database
backups outside the VM, test restoration, rotate logs, apply OS updates, and
monitor API health, bot connectivity, worker failures, disk space, and backup age.
These are deployment tasks to implement, not features supplied by this sample.

## Optional local development (PowerShell)

Run these commands from this worktree's repository root:

```powershell
Set-Location dc_bot
uv python pin 3.15
uv sync --locked
Copy-Item .env.example .env
# Edit .env and fill in your bot token and optional server ID.
uv run bot.py
```

uv manages dependencies from `pyproject.toml` and `uv.lock` and creates a local
`.venv` automatically. This project runs `bot.py` directly without building or
installing a Python package.

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
