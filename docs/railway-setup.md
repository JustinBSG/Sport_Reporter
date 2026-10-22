# Sport Reporter: Railway setup from repository to Discord

Last checked against Railway documentation: **23 October 2026**.

This walkthrough deploys the code in this repository. It creates a persistent
PostgreSQL database, a FastAPI service, and one continuously running Discord bot.
The initial matches are **fictional demo fixtures**, clearly labelled in the API
and Discord. Live sports extraction and automatic scheduled notifications are
future features, not supplied by hosting the starter.

## 1. Understand what you are deploying

```text
Discord users
    | /ping, /sample, /upcoming, /results
    v
discord-bot                    Railway project, same environment/region
    | HTTP + shared bearer key, over private network
    v
backend :8000
    | DATABASE_URL, over private network
    v
Postgres + persistent volume
```

| Service | Source | Public address needed? | Credentials |
| --- | --- | --- | --- |
| `Postgres` | Railway PostgreSQL database | No | Railway creates database credentials |
| `backend` | This repo, root `/backend` | Optional HTTPS address for browser/API testing | `DATABASE_URL`, `SPORT_REPORTER_API_KEY` |
| `discord-bot` | This repo, root `/dc_bot` | No | `DISCORD_TOKEN`, `SPORT_REPORTER_API_KEY`, `BACKEND_URL` |

The bot connects outbound to Discord. It does not need a web server, public port,
Interactions Endpoint URL, or direct database access. Keep all three services in
the **same Railway project and environment**. Singapore is a reasonable initial
region for a Hong Kong-based project; measure latency if needed.

## 2. Check Railway availability and billing

Open [Railway status](https://status.railway.com/) before starting. At the time
this guide was prepared, Railway was recovering from its 21 October 2026 security
incident and the latest retrieved update still restricted Hobby builds. If your
plan cannot deploy, prepare the repository and continue after builds resume.
For an existing affected account, follow Railway's
[security disclosure](https://blog.railway.com/p/security-disclosure-wednesday-october-21st)
and credential rotation guidance before reusing its secrets.

Create/sign in to a [Railway account](https://railway.com/), connect GitHub, and
choose the plan appropriate for continuously running services. Hobby has a $5
minimum monthly usage commitment, which includes $5 usage; it does **not** mean
three continuously running services are guaranteed to cost $5. Set usage alerts
and review CPU, memory, storage, and egress after the first day/week. A hard usage
limit can stop services, so choose its value with that consequence in mind.
See [pricing](https://railway.com/pricing).

## 3. Know the code and deployment files

| File | Purpose |
| --- | --- |
| `backend/app/main.py` | Authenticated API routes and startup/readiness checks |
| `backend/app/models.py` | Match/team models and fictional fixtures |
| `backend/app/repository.py` | PostgreSQL connection pool and parameterized queries |
| `backend/app/db.py` | Versioned migrations and explicit demo seeding commands |
| `backend/app/migrations/001_matches.sql` | Tables, constraints, and indexes |
| `backend/Dockerfile` | Backend image, Python 3.13, locked Python dependencies |
| `dc_bot/bot.py` | Discord slash commands and embeds |
| `dc_bot/backend_client.py` | Async HTTP client with bearer authentication and timeouts |
| `dc_bot/Dockerfile` | Bot image, retaining this project's Python 3.15 requirement |
| Each service's `uv.lock` | Exact dependency resolution used by its Docker build |

The backend runs the equivalent of:

```sh
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Its Docker command also accepts Railway's `PORT`. The bot runs `python bot.py`.
Do not copy Windows `.venv` directories to Railway; Docker builds Linux ones.

This tutorial uses **dashboard settings**, rather than `railway.toml`.
Railway currently deprecates Config as Code for new services; its replacement
is project-level Infrastructure as Code. See
[current configuration guidance](https://docs.railway.com/config-as-code).

## 4. Put this code on GitHub

Commit the application changes, Dockerfiles, SQL migration, and lockfiles to the
branch you want Railway to deploy. Both application directories must be present
on that **same branch**. An older bot-only or backend-only branch will not contain
the complete setup.

From PowerShell in the repository root:

```powershell
git status --short
git branch --show-current
git diff
```

Review and commit the files you intend to deploy, then push your chosen branch.
Never commit `.env`, Discord tokens, API keys, or database URLs. `.gitignore` and
both `.dockerignore` files exclude local credentials and virtual environments.

## 5. Create the Discord application and install the bot

1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
2. Choose **New Application**, name it `Sport Reporter`, and open **Bot**.
3. Create/reset the bot token if required. Save it in your password manager;
   later it becomes the bot service's `DISCORD_TOKEN`. This is the **bot token**,
   not the application ID, public key, or OAuth client secret.
4. Leave privileged Message Content, Members, and Presence intents off. These
   commands use default intents.
5. Under **OAuth2 / URL Generator**, select scopes `bot` and
   `applications.commands`. Grant **View Channels**, **Send Messages**, and
   **Embed Links**. Open the generated URL and install it in a server you manage.
6. Enable Developer Mode in Discord's user settings. Right-click your test
   server and copy its ID. Use it as `DISCORD_GUILD_ID` for fast test registration.
7. Leave the Discord **Interactions Endpoint URL** blank: this bot receives
   commands through its Discord Gateway connection.

Stop any local/VM copy using the same token before starting the Railway bot.
Use one bot replica during this tutorial.

## 6. Create the Railway project and database

1. Create a new **empty project** named `Sport Reporter`.
2. Use one environment, for example the default `production`, throughout.
3. Click **+ New → Database → PostgreSQL**. Name the service **`Postgres`**
   exactly, so the reference expressions below match.
4. Select Singapore for its region when available. Later choose the same region
   for both application services.
5. Wait until PostgreSQL is running. Verify it has its persistent database volume.
   Use the database template's volume configuration; do not attach a volume to
   the backend or bot to store the database.
6. Open the database's **Variables** view. Railway provides `DATABASE_URL`,
   `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, and `PGDATABASE`.
7. Keep the database private. Do not enable a public TCP proxy for this setup.

The database and the tables are separate: Railway creates PostgreSQL; our
migration creates the application tables in the next steps. Railway's current
[PostgreSQL documentation](https://docs.railway.com/databases/postgresql)
describes private-by-default databases and connection variables.

## 7. Create and configure the backend service

1. Choose **+ New → GitHub Repo** and select this repository. Authorize its access
   if GitHub asks. Rename the service **`backend`**.
2. Select the branch containing both application directories and the new files.
3. In **Settings → Source**, set **Root Directory** to `/backend`.
4. Railway should detect the `Dockerfile` in that source directory. Select the
   Dockerfile builder if needed. Leave custom Build Command and Start Command
   empty, allowing the Dockerfile to supply them.
5. Choose the same region as PostgreSQL.
6. Set these deployment settings:

| Backend setting | Value |
| --- | --- |
| Root Directory | `/backend` |
| Builder | Dockerfile, detected from `backend/Dockerfile` |
| Pre-deploy Command, initial demo | `python -m app.db migrate --seed-demo` |
| Healthcheck Path | `/ready` |
| Healthcheck Timeout | `120` seconds |
| Replicas | `1` |
| Restart Policy | On Failure; up to 10 retries if that setting is shown |
| Serverless / App Sleeping | Disabled for this walkthrough |
| Watch Paths, optional | `/backend/**` |

If Railway started an initial deployment before you finished configuration, let
it fail or cancel it; configure the root directory and variables, then redeploy.
Do not treat that initial missing-configuration failure as an application bug.

Root directories are important: backend builds use the `backend` directory as
their Docker build context. See
[Railway monorepos](https://docs.railway.com/deployments/monorepo).

## 8. Set backend environment variables

Open `backend → Variables` and add:

```dotenv
DATABASE_URL=${{Postgres.DATABASE_URL}}
SPORT_REPORTER_API_KEY=PASTE_A_NEW_RANDOM_SECRET_HERE
PORT=8000
```

The `${{...}}` expression is entered literally in Railway, without extra quotes.
It references the `Postgres` service; do not paste it into a local `.env` expecting
your computer to resolve it. Use Railway's reference-variable picker if the
database service has a different name.

Generate an API key **locally**, then paste it into Railway. For example, after
installing Python:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Use your actual Python launcher if it differs. Save the key securely; the bot
will use exactly the same value. Do not put the key in a URL or Git commit.

`DATABASE_URL` should resolve to the database's private hostname. The bot will
not receive this variable. See
[Railway variable references](https://docs.railway.com/variables).

## 9. Deploy, migrate, and seed PostgreSQL

Apply the pending configuration changes and deploy `backend`.

The pre-deploy command runs inside Railway with its variables and private
network access. It applies SQL migrations before the API starts; if it fails,
the deployment stops. See
[pre-deploy commands](https://docs.railway.com/deployments/pre-deploy-command).

Expected log messages include:

```text
Applied 001_matches.sql
Database migrations complete.
Fictional demo rows seeded. Existing rows kept unless --refresh was requested.
Application startup complete.
```

The migration installs:

| Table | Contents |
| --- | --- |
| `schema_migrations` | Applied SQL filenames, preventing repeat application |
| `matches` | Match ID, sport, league, UTC times, status, teams, scores, format, stage, demo flag |

Times use PostgreSQL `TIMESTAMPTZ`. Teams use JSONB objects such as
`{"name":"Sample Tigers","code":"TIG","score":null}`. Match IDs are primary
keys; indexed columns support upcoming/results queries. SQL parameters are bound
separately from values, including match IDs and league filters.

Seeding inserts two future fictional matches and one fictional result. It is
safe to repeat: existing IDs are kept. Ordinary restarts and redeployments do
not recreate their times or erase data. Migrations run transactionally with a
database advisory lock so overlapping deploys cannot apply the same migration.

Open `Postgres → Data` and inspect `matches`; there should be **3 rows**, each
with `is_demo=true`. Open `schema_migrations`; there should be one entry for
`001_matches.sql`.

Once the demo works, change the pre-deploy command to:

```sh
python -m app.db migrate
```

Existing demo rows stay in PostgreSQL. Removing the seeding flag does not delete
them. Before using real data, deliberately remove/replace demo records and add
your real sports extractor; never relabel the fictional rows as real fixtures.

## 10. Verify the backend over HTTPS

For convenient external testing, open `backend → Settings → Networking` and
choose **Generate Domain**, target port **8000**. Railway provides an HTTPS URL.
Public access is optional for normal bot operation; the bot will use private HTTP.

Open `https://YOUR-BACKEND-DOMAIN/ready` in a browser. Expect:

```json
{"status":"ready","data_source":"postgresql"}
```

`/health` confirms that the API is running. `/ready` also queries the database
schema and returns HTTP 503 if it cannot be reached. Railway's deployment
healthcheck is a startup gate, not ongoing uptime monitoring.
See [healthchecks](https://docs.railway.com/deployments/healthchecks).

Open `https://YOUR-BACKEND-DOMAIN/docs`. Select **Authorize**, enter only your API
key into the bearer field, then try:

| Request | Expected result |
| --- | --- |
| `GET /upcoming?hours=24` | Two fictional upcoming matches, soon after first seeding |
| `GET /upcoming?leagues=lck` | One fictional LoL match |
| `GET /matches/lol-sample-result` | Fictional completed match with score 3–1 |
| `GET /results?since=2026-01-01T00:00:00Z` | Demo result seeded after that timestamp |
| A match endpoint without the key | HTTP 401 |

Equivalent PowerShell, replacing the URL and key locally:

```powershell
$apiBase = 'https://YOUR-BACKEND-DOMAIN'
$apiHeaders = @{ Authorization = 'Bearer YOUR_API_KEY' }
Invoke-RestMethod "$apiBase/ready"
Invoke-RestMethod "$apiBase/upcoming?hours=24" -Headers $apiHeaders
Invoke-RestMethod "$apiBase/matches/lol-sample-result" -Headers $apiHeaders
$since = [Uri]::EscapeDataString([DateTimeOffset]::UtcNow.AddHours(-24).ToString('o'))
Invoke-RestMethod "$apiBase/results?since=$since" -Headers $apiHeaders
```

The API returns at most 100 rows per upcoming/results request. There is no
pagination yet; add it before building an extractor/client that needs every row
from larger windows.

## 11. Create and configure the Discord bot service

1. In the **same project and environment**, add the **same GitHub repository**
   again as a second service. This is a second deployment, not a second repo.
2. Rename it **`discord-bot`** and choose the same branch.
3. Set **Root Directory** to `/dc_bot`.
4. Let Railway detect `dc_bot/Dockerfile`. Leave custom build/start commands empty.
5. Choose the same region as the backend and database.
6. Use these settings:

| Bot setting | Value |
| --- | --- |
| Root Directory | `/dc_bot` |
| Builder | Dockerfile |
| Start Command | Leave empty; Docker runs `python bot.py` |
| Pre-deploy Command | Empty |
| HTTP Healthcheck | Empty; this worker has no HTTP listener |
| Replicas | `1` |
| Restart Policy | On Failure; up to 10 retries if available |
| Serverless / App Sleeping | Disabled |
| Public domain | None |
| Watch Paths, optional | `/dc_bot/**` |

Do not configure a cron schedule: a Discord Gateway bot must keep running.
One replica avoids handling the same interactions in multiple independent bot
processes. Brief deployment overlap is still possible; do not run a second
local or VM copy using this token.

## 12. Set bot variables and deploy

Open `discord-bot → Variables`:

```dotenv
DISCORD_TOKEN=PASTE_THE_DISCORD_BOT_TOKEN
DISCORD_GUILD_ID=PASTE_YOUR_TEST_SERVER_ID
SPORT_REPORTER_API_KEY=${{backend.SPORT_REPORTER_API_KEY}}
BACKEND_URL=http://${{backend.RAILWAY_PRIVATE_DOMAIN}}:8000
```

Use the literal reference expressions, without extra quotes. `backend` must match
the actual service name. `BACKEND_URL` is the **API origin**, with its port and no
`/docs` or `/upcoming` suffix. Internal HTTP stays inside Railway's private network;
use HTTPS for external access. See
[private networking practices](https://docs.railway.com/overview/best-practices).

Deploy the bot. Its logs should show `Synced 4 slash commands` and
`Sport Reporter is online as ...`. The bot does not require the backend to be
available at login; API commands show an error until the backend is ready.

Never add `DATABASE_URL` to the bot. The API owns database access and the bot
receives only the read API's bearer key.

## 13. Verify from Discord

In a channel where the bot can read/send messages and embed links:

```text
/ping
/sample
/upcoming hours:24
/upcoming hours:24 leagues:lck
/results hours:24
```

`/ping` tests the bot's Discord connection. `/sample` creates a fictional embed
locally, so it does not test the backend. `/upcoming` and `/results` verify the
complete path through the API to PostgreSQL. These API command replies are
private to the invoking user and show at most ten embeds per response.

Demo timestamps were created when you first seeded the database. After the demo
start times pass, `/upcoming` correctly returns no matches. This is not data loss.
Refresh the demonstration timestamps using the optional SSH procedure below.

Disconnect your computer from the internet or close your local terminals and
repeat `/ping` and `/results` from Discord on your phone. The hosted bot continues
running independently of your computer.

## 14. Optional: run database maintenance through Railway SSH

Install the Railway CLI using its [official CLI instructions](https://docs.railway.com/cli).
For a computer that already has Node.js/npm:

```powershell
npm install -g @railway/cli
railway login
railway link
```

During `link`, select the correct project and environment. Then:

```powershell
railway ssh --service backend -- python -m app.db migrate
railway ssh --service backend -- python -m app.db seed-demo --refresh
```

The second command intentionally moves only the three known demo IDs' timestamps
to the current demonstration window. It does not update rows with `is_demo=false`.
Do not run it as a scheduled task or confuse it with live data collection.

The first SSH connection may ask you to register your SSH key. Alternatively,
right-click the backend service in Railway and use **Copy SSH Command**, open its
shell, and run `python -m app.db ...` there.
See [Railway SSH](https://docs.railway.com/cli/ssh).

Do not use `railway run` on your PC expecting it to join Railway's private
network: it runs locally with supplied environment variables. The private
`*.railway.internal` database hostname is for deployed services.

## 15. Backups, persistence, updates, and recovery

1. Open the PostgreSQL service/volume's **Backups** settings and enable scheduled
   backups. The exact tab placement may vary. Create a manual backup before a
   schema change. Check the additional storage cost.
2. If you need recovery between snapshots, enable PostgreSQL **point-in-time
   recovery** following Railway's current database settings. This is an explicit
   configuration step, not something the app migration enables.
3. Test a restore into a separate database/service before you need it. Verify row
   counts and a known match using that restored database before switching the
   backend's `DATABASE_URL`. Keep an independent export for recovery elsewhere.
4. Verify persistence: note a match ID and timestamp in `Postgres → Data`,
   redeploy `backend`, and confirm the same values remain. Redeploying the app
   does not delete the database volume.
5. For updates, commit and push the intended branch; Railway can redeploy the
   affected services. Check migration logs, `/ready`, `/ping`, and API commands.
6. Add each future schema change as a **new numbered `.sql` file**. Do not edit
   an already applied migration. The runner tracks filenames and applies pending
   files in order. Use backward-compatible changes when old/new app versions
   might briefly run together.
7. Rolling back an app deployment does not undo its database migrations. Back up
   before destructive changes and plan a database-compatible rollback.

Reference: [volume backups](https://docs.railway.com/volumes/backups),
[point-in-time recovery](https://docs.railway.com/volumes/point-in-time-recovery),
[database responsibilities](https://docs.railway.com/databases).

## 16. Local development and tests, optional

Install [uv](https://docs.astral.sh/uv/getting-started/installation/). The backend
supports Python 3.11+; its Docker image uses 3.13. The bot retains the repository's
Python 3.15 requirement. `uv` can install the required Python versions.

For a local database, install PostgreSQL or start Docker Desktop and run:

```powershell
docker run --name sport-reporter-postgres -e POSTGRES_USER=sport -e POSTGRES_PASSWORD=local-dev-only -e POSTGRES_DB=sport_reporter -p 127.0.0.1:5432:5432 -v sport-reporter-pgdata:/var/lib/postgresql/data -d postgres:17
```

This binds PostgreSQL to localhost and keeps its data in a named Docker volume.
On later sessions, use `docker start sport-reporter-postgres`, not another
`docker run` with the same name. Wait until its logs say it is ready for connections.

Backend terminal, from the repository root:

```powershell
Set-Location backend
uv sync --locked --extra dev --python 3.13
$env:DATABASE_URL = 'postgresql://sport:local-dev-only@127.0.0.1:5432/sport_reporter'
$env:SPORT_REPORTER_API_KEY = 'local-test-key-change-before-hosting'
uv run --python 3.13 python -m app.db migrate --seed-demo
uv run --python 3.13 python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The backend reads process environment variables; it does not automatically load
`.env`. Do not use `--reload` on Railway. Local memory-only mode is still available
by leaving `DATABASE_URL` unset; Railway refuses that fallback.

Bot terminal, from the repository root:

```powershell
Set-Location dc_bot
uv sync --locked --extra dev
# Create .env only if it does not already exist; preserve any existing token.
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
uv run python bot.py
```

Set the bot's `.env` to your token/server ID, `BACKEND_URL=http://127.0.0.1:8000`,
and `SPORT_REPORTER_API_KEY=local-test-key-change-before-hosting`. Stop the Railway
bot first or use a separate development bot token.

Run tests from each service's directory:

```powershell
# backend terminal, with local PostgreSQL already running
$env:TEST_DATABASE_URL = 'postgresql://sport:local-dev-only@127.0.0.1:5432/sport_reporter'
uv run --python 3.13 pytest -q
```

```powershell
# dc_bot terminal
uv run pytest -q
```

Database tests use a unique temporary schema and remove only that schema. Without
`TEST_DATABASE_URL`, the real PostgreSQL tests are skipped. Test the migration and
query path with a disposable local database before production deployment.

## 17. Troubleshooting

| Symptom | Check |
| --- | --- |
| Root Dockerfile/build not found | Set `/backend` or `/dc_bot` as that service's Root Directory, on the correct branch |
| Lockfile out of date | Run `uv lock` in the changed service, commit its `uv.lock`, then redeploy |
| API startup says `DATABASE_URL` missing | Add `${{Postgres.DATABASE_URL}}` to the backend; apply pending changes |
| Migration times out | Database running, same environment, correct private URL, correct region/network |
| `relation matches does not exist` | Set backend pre-deploy command to `python -m app.db migrate` and redeploy |
| Backend healthcheck fails | `PORT=8000`, healthcheck `/ready`, successful migration, correct database variables |
| HTTP 401 | Bot and backend must use the identical API key; use the reference variable and redeploy |
| Bot rejects its token | Use the Discord Bot token, without `Bot ` prefix, spaces or extra quotes |
| Slash commands absent | Bot invited with `applications.commands`, correct server ID, sync succeeded, Discord role allows commands |
| Global commands slow to appear | Use your test `DISCORD_GUILD_ID` initially; global commands propagate separately |
| Duplicate commands after switching guild/global | Old command registrations can remain; keep the development guild setting consistent and deliberately clean the old scope |
| `/sample` works, API commands fail | `/sample` is local; check `BACKEND_URL`, bearer key, and backend `/ready` |
| `/upcoming` returns no demo matches | Original demo start times may have passed; refresh them deliberately with the SSH command |
| Data disappears on restart | `/ready` must report `postgresql`; inspect PostgreSQL's persistent volume and actual connection target |
| Bot offline | Inspect crashes/logs, token, account usage limit, and sleeping setting; the bot needs no public domain |
| Hobby deployment cannot start | Check Railway status for the current plan-specific deployment restrictions |

## 18. What to build after deployment

You now have persistent match storage, a protected read API, and a bot that queries
it on demand. A complete sports notification product additionally needs a sports
data provider, an idempotent extraction/upsert worker, subscription/channel
preferences, and a persistent notification log with retry/deduplication rules.
Those features should be added explicitly; hosting alone does not fetch real
matches or send scheduled alerts.
