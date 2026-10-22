# Sport Reporter backend

FastAPI read API for sports matches, backed by PostgreSQL when `DATABASE_URL` is
set. With no database URL, local development uses fictional in-memory fixtures.
On Railway the database URL is mandatory, preventing accidental volatile storage.
Demo matches always have `is_demo=true`; no live sports extractor is included yet.

## Deploy to Railway

Follow the [complete Railway tutorial](../docs/railway-setup.md). Deploy this
folder as the `backend` service, with root directory `/backend` and its Dockerfile.
The image uses Python 3.13 and installs dependencies from `uv.lock`.

Required variables:

```dotenv
DATABASE_URL=${{Postgres.DATABASE_URL}}
SPORT_REPORTER_API_KEY=your-random-secret
PORT=8000
```

In Railway's dashboard set the pre-deploy command to `python -m app.db migrate`
(or `python -m app.db migrate --seed-demo` for the first fictional demo), healthcheck
path `/ready`, and one replica. The Dockerfile supplies the start command.

## Run locally (PowerShell)

From this directory, with [uv](https://docs.astral.sh/uv/) installed:

```powershell
uv sync --locked --extra dev --python 3.13
$env:SPORT_REPORTER_API_KEY = 'local-test-key-change-before-hosting'
# Optional: leave DATABASE_URL unset for local in-memory sample mode.
$env:DATABASE_URL = 'postgresql://sport:local-dev-only@127.0.0.1:5432/sport_reporter'
uv run --python 3.13 python -m app.db migrate --seed-demo
uv run --python 3.13 python -m uvicorn app.main:app --reload
```

For memory-only mode, omit the database variable and migration command.
The backend reads process environment variables; it does not load `.env` itself.
Open `http://127.0.0.1:8000/docs`, select **Authorize**, and enter your bearer key.

## API

| Route | Behavior |
| --- | --- |
| `GET /health` | Public liveness and storage source (`sample` or `postgresql`) |
| `GET /ready` | Public readiness, including a database schema query |
| `GET /upcoming?hours=24&leagues=lck,nba` | Unstarted matches in the next 1–168 hours |
| `GET /results?since=<ISO timestamp>&leagues=worlds` | Completed matches updated at or after `since` |
| `GET /matches/{id}` | One match, or HTTP 404 |

Match endpoints require `Authorization: Bearer <SPORT_REPORTER_API_KEY>`.
League filters are optional, comma separated, and case insensitive. Times include
UTC offsets; `since` must be timezone aware. PostgreSQL list queries return at
most 100 rows, ordered by start/update time and ID. Pagination is not implemented.
Clients polling results should deduplicate by ID and update time because the
`since` boundary is inclusive. The bot currently queries on demand, without polling.

## Database lifecycle

- `python -m app.db migrate`: apply new SQL files from `app/migrations` once.
- `python -m app.db migrate --seed-demo`: also insert missing fictional examples.
- `python -m app.db seed-demo --refresh`: deliberately move only the known demo
  records' timestamps to the current demonstration window.

`DATABASE_URL` is required for these commands. Production startup does not seed
or reset records. A separate migration ledger and transaction advisory lock
protect repeat/concurrent migrations. Add new numbered SQL files for changes;
do not edit applied migrations. Enable Railway backups separately.

## Tests

```powershell
uv run --python 3.13 pytest -q
```

Set `TEST_DATABASE_URL` to a disposable local PostgreSQL connection string to run
real database integration tests too. They create and remove a unique temporary
schema. Without it, those checks are skipped. API-only tests use memory fixtures.
