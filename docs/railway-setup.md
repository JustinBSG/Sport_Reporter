# Sport Reporter: Railway setup guide

Guide date: **October 23, 2026**.

This guide deploys the code in this repository. The deployment has a persistent
PostgreSQL database, a FastAPI backend, and one Discord bot that runs continuously.

The initial matches are fictional demo data. The API and Discord replies identify
these records as demo data. The application does not collect live sports data or
send scheduled notifications. These features require more development.

## 1. Identify the services

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

| Service | Source | Public address | Credentials |
| --- | --- | --- | --- |
| `Postgres` | Railway PostgreSQL database | Not required | Railway creates database credentials |
| `backend` | Repository root directory `/backend` | Optional HTTPS address for external tests | `DATABASE_URL`, `SPORT_REPORTER_API_KEY` |
| `discord-bot` | Repository root directory `/dc_bot` | Not required | `DISCORD_TOKEN`, `SPORT_REPORTER_API_KEY`, `BACKEND_URL` |

The bot makes an outbound connection to Discord. It does not need a web server,
public port, Interactions Endpoint URL, or database credentials.

Keep all three services in the same Railway project, environment, and region.
For a project in Hong Kong, Singapore is an initial region option. Measure latency
if you need to compare regions.

## 2. Check Railway status and billing

1. Open [Railway status](https://status.railway.com/).
2. Check for incidents or deployment restrictions that affect your plan.
3. If deployments are unavailable, prepare the repository until service resumes.
4. If an incident affects your account, obey Railway's instructions to replace credentials.

See Railway's [security disclosure](https://blog.railway.com/p/security-disclosure-wednesday-october-21st)
for its October 21, 2026 incident guidance.

5. Create an account or sign in to [Railway](https://railway.com/).
6. Connect your GitHub account.
7. Select a plan for services that run continuously.
8. Set usage alerts.
9. Review CPU, memory, storage, and network charges after the first day and week.

The Hobby plan has a $5 monthly minimum, which includes $5 of resource usage.
Usage above this amount costs extra. Three services can cost more than $5 per
month. A hard usage limit can stop services. See [Railway pricing](https://railway.com/pricing)
for current prices.

## 3. Identify the deployment files

| File | Purpose |
| --- | --- |
| `backend/app/main.py` | API routes, authentication, startup, and readiness checks |
| `backend/app/models.py` | Match models, team models, and fictional demo records |
| `backend/app/repository.py` | PostgreSQL connection pool and queries with bound parameters |
| `backend/app/db.py` | Migration commands and demo data commands |
| `backend/app/migrations/001_matches.sql` | Database tables, constraints, and indexes |
| `backend/Dockerfile` | Backend image with Python 3.13 and locked dependencies |
| `dc_bot/bot.py` | Discord slash commands and match embeds |
| `dc_bot/backend_client.py` | Asynchronous HTTP client with bearer authentication and timeouts |
| `dc_bot/Dockerfile` | Bot image with Python 3.15 |
| Each service's `uv.lock` | Exact dependency versions for its Docker build |

The backend runs the equivalent of this command:

```sh
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The Docker start command also accepts Railway's `PORT` variable. The bot runs
`python bot.py`. Docker creates Linux virtual environments during the build.
Do not copy Windows `.venv` directories to Railway.

This guide uses Railway dashboard settings. Railway has deprecated Config as
Code for new services. Its replacement is project-level Infrastructure as Code.
See the [configuration guidance](https://docs.railway.com/config-as-code).

## 4. Prepare the GitHub branch

Both application directories must be on the branch that Railway deploys. This
branch must also contain the Dockerfiles, SQL migration, and lockfiles.

1. Open PowerShell in the repository root.
2. Check the working tree:

   ```powershell
   git status --short
   git branch --show-current
   git diff
   ```

3. Review the files that you intend to deploy.
4. Commit these files to the deployment branch.
5. Push the branch to GitHub.

Never commit `.env`, Discord tokens, API keys, or database URLs. `.gitignore` and
both `.dockerignore` files exclude local credentials and virtual environments.

## 5. Create the Discord application

1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
2. Select **New Application**.
3. Name the application `Sport Reporter`.
4. Open **Bot**.
5. If necessary, create or reset the bot token.
6. Save the token in your password manager.

The bot service uses this token as `DISCORD_TOKEN`. The application ID, public
key, and OAuth client secret cannot replace the bot token.

7. Leave the privileged Message Content, Members, and Presence intents disabled.
8. Open **OAuth2 / URL Generator**.
9. Select the scopes `bot` and `applications.commands`.
10. Grant **View Channels**, **Send Messages**, and **Embed Links**.
11. Open the generated installation URL.
12. Install the bot in a server that you manage.
13. Enable Developer Mode in Discord's user settings.
14. Copy your test server ID from the server's context menu.
15. Use this ID as `DISCORD_GUILD_ID` for test command registration.
16. Leave **Interactions Endpoint URL** blank.
17. Stop local or VM bot processes that use the same token.

The bot receives commands through its Discord Gateway connection. Use one bot
replica for this guide.

## 6. Create the Railway project and database

1. Create an empty Railway project named `Sport Reporter`.
2. Select one environment, such as the default `production`.
3. Select **+ New > Database > PostgreSQL**.
4. Name the database service `Postgres`.
5. If available, select the Singapore region.
6. Wait until PostgreSQL is running.
7. Make sure that the database service has a persistent volume.
8. Use the database template's volume configuration.
9. Open the database's **Variables** view.
10. Keep the database private.
11. Leave the public TCP proxy disabled.

The name `Postgres` must match the variable references in this guide. Both
application services must use the same environment and region as the database.
Do not attach a database storage volume to the backend or bot.

Railway supplies `DATABASE_URL`, `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, and
`PGDATABASE`. Railway creates the database service. The application migration
creates its tables later. See the [PostgreSQL documentation](https://docs.railway.com/databases/postgresql).

## 7. Configure the backend service

1. Select **+ New > GitHub Repo**.
2. Select this repository.
3. If GitHub requests access permission, authorize repository access.
4. Rename the service `backend`.
5. Select the branch with both application directories and deployment files.
6. Open **Settings > Source**.
7. Set **Root Directory** to `/backend`.
8. If necessary, select the Dockerfile builder.
9. Leave custom **Build Command** and **Start Command** empty.
10. Select the database's region.
11. Apply these deployment settings:

| Backend setting | Value |
| --- | --- |
| Root Directory | `/backend` |
| Builder | Dockerfile from `backend/Dockerfile` |
| Pre-deploy Command for the first demo | `python -m app.db migrate --seed-demo` |
| Healthcheck Path | `/ready` |
| Healthcheck Timeout | `120` seconds |
| Replicas | `1` |
| Restart Policy | On Failure; maximum 10 retries if available |
| Serverless / App Sleeping | Disabled |
| Watch Paths, optional | `/backend/**` |

Railway uses the `backend` directory as the Docker build context. The Dockerfile
supplies the build and start commands. See [Railway monorepos](https://docs.railway.com/deployments/monorepo).

An initial deployment can start before configuration is complete. If this occurs,
cancel the deployment or let it fail. Complete the settings and variables before
you deploy again. This initial failure can result from missing configuration.

## 8. Set backend variables

1. Open **backend > Variables**.
2. Add these variables:

   ```dotenv
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   SPORT_REPORTER_API_KEY=PASTE_A_NEW_RANDOM_SECRET_HERE
   PORT=8000
   ```

Enter `${{...}}` references exactly as shown, without extra quotes. Railway
resolves these references. A local `.env` file does not resolve them. If the
database service has another name, use Railway's reference-variable selector.

3. Generate an API key on your computer:

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

4. If your Python launcher differs, use that launcher.
5. Replace `PASTE_A_NEW_RANDOM_SECRET_HERE` with the generated key.
6. Save the key in secure storage.
7. Make sure that `DATABASE_URL` resolves to the database's private hostname.

The bot must use the same API key. Do not put the key in a URL or Git commit.
Do not give `DATABASE_URL` to the bot. See [variable references](https://docs.railway.com/variables).

## 9. Deploy the backend and create demo records

1. Apply the pending backend configuration changes.
2. Deploy `backend`.
3. Check the deployment logs.

The pre-deploy command uses Railway's environment variables and private network.
It applies SQL migrations before the API starts. A command failure stops the
deployment. See [pre-deploy commands](https://docs.railway.com/deployments/pre-deploy-command).

Expected log messages include:

```text
Applied 001_matches.sql
Database migrations complete.
Fictional demo rows seeded. Existing rows kept unless --refresh was requested.
Application startup complete.
```

The migration creates these tables:

| Table | Contents |
| --- | --- |
| `schema_migrations` | Names of applied SQL files |
| `matches` | ID, sport, league, UTC times, status, teams, scores, format, stage, and demo flag |

Timestamps use PostgreSQL `TIMESTAMPTZ`. Teams use JSONB objects, such as
`{"name":"Sample Tigers","code":"TIG","score":null}`. Match IDs are primary
keys. Indexes support queries for upcoming matches and results. Queries bind
parameter values separately from SQL, including match IDs and league filters.

The demo command inserts two future matches and one result. All three matches
are fictional. Repeated runs keep existing IDs. Normal restarts and deployments
do not reset timestamps or erase records.

Each migration run uses a transaction and a database advisory lock. The lock
prevents concurrent deployments from applying the same migration.

4. Open **Postgres > Data**.
5. Inspect `matches` for three records with `is_demo=true`.
6. Inspect `schema_migrations` for one entry named `001_matches.sql`.
7. After the demo works, change the pre-deploy command to:

   ```sh
   python -m app.db migrate
   ```

This change leaves the demo records in PostgreSQL. Before you use real data,
remove or replace the demo records. Add a sports data extractor to collect real
matches. Never change fictional records to identify them as real matches.

## 10. Check the backend over HTTPS

A public domain is optional. The bot uses Railway's private network for normal
operation.

1. For external tests, open **backend > Settings > Networking**.
2. Select **Generate Domain**.
3. Set the target port to `8000`.
4. Open `https://YOUR-BACKEND-DOMAIN/ready` in a browser.

Expected response:

```json
{"status":"ready","data_source":"postgresql"}
```

`/health` confirms that the API is running. `/ready` also queries the database
schema. It returns HTTP 503 if the database check fails. Railway checks readiness
before it activates a deployment. It does not continue to monitor the endpoint
after deployment. See [healthchecks](https://docs.railway.com/deployments/healthchecks).

5. Open `https://YOUR-BACKEND-DOMAIN/docs`.
6. Select **Authorize**.
7. Enter only the API key in the bearer field.
8. Send these test requests:

| Request | Expected result |
| --- | --- |
| `GET /upcoming?hours=24` | Two fictional upcoming matches soon after the first demo insertion |
| `GET /upcoming?leagues=lck` | One fictional LoL match |
| `GET /matches/lol-sample-result` | A fictional completed match with a 3-1 score |
| `GET /results?since=2026-01-01T00:00:00Z` | The demo result, if its update time is after this timestamp |
| A match route without the API key | HTTP 401 |

To check the same routes from PowerShell, replace the URL and key in this example:

```powershell
$apiBase = 'https://YOUR-BACKEND-DOMAIN'
$apiHeaders = @{ Authorization = 'Bearer YOUR_API_KEY' }
Invoke-RestMethod "$apiBase/ready"
Invoke-RestMethod "$apiBase/upcoming?hours=24" -Headers $apiHeaders
Invoke-RestMethod "$apiBase/matches/lol-sample-result" -Headers $apiHeaders
$since = [Uri]::EscapeDataString([DateTimeOffset]::UtcNow.AddHours(-24).ToString('o'))
Invoke-RestMethod "$apiBase/results?since=$since" -Headers $apiHeaders
```

PostgreSQL list queries return a maximum of 100 records. The API does not support
pagination. Add pagination before a client requires all records from a larger
query period.

## 11. Configure the Discord bot service

1. Add the same GitHub repository as a second service in the same Railway project and environment.
2. Rename the service `discord-bot`.
3. Select the backend's deployment branch.
4. Set **Root Directory** to `/dc_bot`.
5. Use the Dockerfile from `dc_bot/Dockerfile`.
6. Leave custom build and start commands empty.
7. Select the backend's region.
8. Apply these settings:

| Bot setting | Value |
| --- | --- |
| Root Directory | `/dc_bot` |
| Builder | Dockerfile |
| Start Command | Empty; Docker runs `python bot.py` |
| Pre-deploy Command | Empty |
| HTTP Healthcheck | Empty; the bot has no HTTP listener |
| Replicas | `1` |
| Restart Policy | On Failure; maximum 10 retries if available |
| Serverless / App Sleeping | Disabled |
| Public domain | None |
| Watch Paths, optional | `/dc_bot/**` |

This creates a second deployment of the repository. It does not require another
repository. A Discord Gateway bot must run continuously. Do not set a cron
schedule for this service.

One replica prevents multiple independent bot processes from handling the same
interaction. Old and new processes can briefly overlap during deployment. Do
not run a local or VM bot process with the same token.

## 12. Set bot variables and deploy

1. Open **discord-bot > Variables**.
2. Add these variables:

   ```dotenv
   DISCORD_TOKEN=PASTE_THE_DISCORD_BOT_TOKEN
   DISCORD_GUILD_ID=PASTE_YOUR_TEST_SERVER_ID
   SPORT_REPORTER_API_KEY=${{backend.SPORT_REPORTER_API_KEY}}
   BACKEND_URL=http://${{backend.RAILWAY_PRIVATE_DOMAIN}}:8000
   ```

Enter the references exactly as shown, without extra quotes. `backend` must
match the API service name. `BACKEND_URL` is the API origin: scheme, hostname,
and port. Do not add `/docs`, `/upcoming`, or another path.

Internal HTTP stays within Railway's private network. Use HTTPS for external
access. See [private networking guidance](https://docs.railway.com/overview/best-practices).

3. Deploy the bot.
4. Check its logs for `Synced 4 slash commands` and `Sport Reporter is online as ...`.

The bot can connect to Discord before the backend is ready. API commands return
an error until the backend is available. The bot receives only the API key for
read access. Never add `DATABASE_URL` to the bot.

## 13. Check the bot in Discord

1. Open a channel where the bot has View Channels, Send Messages, and Embed Links permissions.
2. Send these commands one at a time:

   ```text
   /ping
   /sample
   /upcoming hours:24
   /upcoming hours:24 leagues:lck
   /results hours:24
   ```

`/ping` checks the Discord connection. `/sample` creates a fictional embed
locally. It does not check the backend. `/upcoming` and `/results` check the
connection through the API to PostgreSQL. Their replies are private to the user
who sends the command. Each response contains a maximum of ten embeds.

The first demo insertion sets the timestamps. After the start times pass,
`/upcoming` returns no demo matches. The records remain in the database. Use the
optional SSH procedure in section 14 to move the demo timestamps.

3. Disconnect your computer from the internet or close its local terminals.
4. Send `/ping` and `/results` from Discord on your phone.

The hosted bot continues to run independently of your computer.

## 14. Run database maintenance through Railway SSH, optional

Use the [Railway CLI installation instructions](https://docs.railway.com/cli).
If Node.js and npm are already installed, use these commands:

```powershell
npm install -g @railway/cli
railway login
railway link
```

1. During `railway link`, select the correct project and environment.
2. To apply pending migrations, run:

   ```powershell
   railway ssh --service backend -- python -m app.db migrate
   ```

3. To move demo timestamps to the current demo period, run:

   ```powershell
   railway ssh --service backend -- python -m app.db seed-demo --refresh
   ```

The refresh command affects only the three known demo IDs. It does not update
records with `is_demo=false`. It also inserts a known demo record if that record
is missing. Do not schedule this command. It does not collect live data.

The first SSH connection can require SSH key registration. As an alternative:

1. Open the backend service's context menu in Railway.
2. Select **Copy SSH Command**.
3. Use the copied command to open a shell.
4. Run the required `python -m app.db ...` command in that shell.

See [Railway SSH](https://docs.railway.com/cli/ssh).

`railway run` executes locally with supplied environment variables. It does not
connect your computer to Railway's private network. Private
`*.railway.internal` database hostnames are for deployed services.

## 15. Configure backups and recovery

1. Open the PostgreSQL service or volume's **Backups** settings.
2. Enable scheduled backups.
3. Check the additional storage cost.
4. Before a schema change, create a manual backup.
5. If you need recovery between snapshots, enable PostgreSQL **point-in-time recovery**.
6. Test a restore into a separate database or service.
7. Check record counts and a known match in the restored database.
8. After these checks pass, change the backend's `DATABASE_URL` if required.
9. Keep an independent database export for recovery on another host.

The location of backup settings can change. Application migrations do not enable
backups or point-in-time recovery. Use Railway's current settings. See
[volume backups](https://docs.railway.com/volumes/backups),
[point-in-time recovery](https://docs.railway.com/volumes/point-in-time-recovery),
and [database responsibilities](https://docs.railway.com/databases).

To check persistence:

1. Record a match ID and timestamp from **Postgres > Data**.
2. Deploy `backend` again.
3. Make sure that the match ID and timestamp have not changed.

An application deployment does not delete the database volume.

To update the application:

1. Commit the intended changes to the deployment branch.
2. Push the branch to GitHub.
3. Check Railway's deployments for the affected services.
4. Check migration logs, `/ready`, `/ping`, and the API commands.

For each schema change, add a new numbered `.sql` file. Do not change an applied
migration. The migration runner records filenames and applies new files in
order. Use compatible schema changes when old and new application versions can
run at the same time.

An application rollback does not reverse database migrations. Before a change
that deletes or alters data, make a backup. Plan a rollback that works with the
resulting database schema.

## 16. Run locally and test, optional

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) before you
start. The backend supports Python 3.11 or later. Its Docker image uses Python
3.13. The bot requires Python 3.15 or later. `uv` can install these Python versions.

### Start local PostgreSQL

Use an installed PostgreSQL server, or start Docker Desktop and run:

```powershell
docker run --name sport-reporter-postgres -e POSTGRES_USER=sport -e POSTGRES_PASSWORD=local-dev-only -e POSTGRES_DB=sport_reporter -p 127.0.0.1:5432:5432 -v sport-reporter-pgdata:/var/lib/postgresql/data -d postgres:17
```

This command binds PostgreSQL to localhost. A named Docker volume stores the
data. For later sessions, use `docker start sport-reporter-postgres`. Do not
repeat `docker run` with the same container name. Wait until the logs show that
PostgreSQL is ready for connections.

### Start the backend

Run these commands in a terminal at the repository root:

```powershell
Set-Location backend
uv sync --locked --extra dev --python 3.13
$env:DATABASE_URL = 'postgresql://sport:local-dev-only@127.0.0.1:5432/sport_reporter'
$env:SPORT_REPORTER_API_KEY = 'local-test-key-change-before-hosting'
uv run --python 3.13 python -m app.db migrate --seed-demo
uv run --python 3.13 python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The backend reads process environment variables. It does not load `.env`. For
local demo data in memory, leave `DATABASE_URL` unset and omit the migration
command. Railway requires PostgreSQL. Do not use `--reload` on Railway.

### Start the bot

Run these commands in a separate terminal at the repository root:

```powershell
Set-Location dc_bot
uv sync --locked --extra dev
# Create .env only if the file does not exist.
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
uv run python bot.py
```

Before you run `bot.py`, save these values in `.env`:

- Your bot token and test server ID.
- `BACKEND_URL=http://127.0.0.1:8000`.
- `SPORT_REPORTER_API_KEY=local-test-key-change-before-hosting`.

Stop the Railway bot before you start a local bot with the same token. To keep
the hosted bot running, use a separate development bot token.

### Run tests

From the `backend` directory, with local PostgreSQL running:

```powershell
$env:TEST_DATABASE_URL = 'postgresql://sport:local-dev-only@127.0.0.1:5432/sport_reporter'
uv run --python 3.13 pytest -q
```

From the `dc_bot` directory:

```powershell
uv run pytest -q
```

Database tests create a unique temporary schema. They remove only that schema
after the test. Without `TEST_DATABASE_URL`, PostgreSQL integration tests do not
run. Before production deployment, check migrations and queries with a disposable
local database.

## 17. Troubleshooting

| Problem | Action |
| --- | --- |
| Dockerfile or build source missing | Check the branch and Root Directory: `/backend` or `/dc_bot` |
| Lockfile out of date | Run `uv lock` in the affected service. Commit `uv.lock`. Deploy again |
| API reports missing `DATABASE_URL` | Add `${{Postgres.DATABASE_URL}}` to the backend. Apply pending changes |
| Migration timeout | Check database status, environment, private URL, region, and network |
| `relation matches does not exist` | Set the backend pre-deploy command to `python -m app.db migrate`. Deploy again |
| Backend healthcheck failure | Check `PORT=8000`, `/ready`, migration logs, and database variables |
| HTTP 401 | Use the same API key on both services. Check the reference variable. Deploy again |
| Bot token rejected | Use the Discord Bot token without a `Bot ` prefix, spaces, or extra quotes |
| Slash commands missing | Check the installation scope `applications.commands`, server ID, registration logs, and command permissions |
| Global commands appear slowly | Use the test server's `DISCORD_GUILD_ID` during development |
| Duplicate server and global commands | Keep the development server setting consistent. Remove registrations from the old scope |
| `/sample` works but API commands fail | Check `BACKEND_URL`, the API key, and backend `/ready` |
| No upcoming demo matches | Check whether demo start times have passed. Use section 14 to move their timestamps |
| Data missing after restart | Check that `/ready` reports `postgresql`. Inspect the database volume and connection target |
| Bot offline | Check logs, crashes, token, account usage limit, and app sleeping |
| Railway deployment unavailable | Check Railway status for restrictions that affect your plan |

## 18. Plan the next features

After deployment, the application provides persistent match storage, a protected
read API, and a bot that responds to commands.

A complete sports notification system also needs:

- A sports data provider.
- An extractor that inserts new records and updates existing records without duplicates.
- Subscription and channel preferences.
- A persistent notification log.
- Retry rules and duplicate checks for notifications.

These features require development. Hosting the current application does not
collect real matches or send scheduled alerts.
