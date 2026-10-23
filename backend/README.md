# Sport Reporter backend

The backend uses FastAPI to provide read access to sports matches. It uses
PostgreSQL when you set `DATABASE_URL`. Without this variable, local development
uses fictional demo matches in memory. Railway requires `DATABASE_URL` to prevent
the use of temporary storage.

Demo records have `is_demo=true`. The backend does not collect live sports data.

## Deploy to Railway

Use the [Railway setup guide](../docs/railway-setup.md) for the complete procedure.

1. Create a service named `backend` from this repository.
2. Set its root directory to `/backend`.
3. Use the Dockerfile in this directory.
4. Add these environment variables:

   ```dotenv
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   SPORT_REPORTER_API_KEY=your-random-secret
   PORT=8000
   ```

5. Set the pre-deploy command to `python -m app.db migrate`.
6. For the first demo deployment, use `python -m app.db migrate --seed-demo` instead.
7. Set the healthcheck path to `/ready`.
8. Set the replica count to `1`.

The Dockerfile supplies the start command. Its image uses Python 3.13 and the
dependencies in `uv.lock`.

## Run locally with PowerShell

Install [uv](https://docs.astral.sh/uv/) before you start.

1. Open PowerShell in the `backend` directory.
2. Install the dependencies:

   ```powershell
   uv sync --locked --extra dev --python 3.13
   ```

3. Set an API key for local tests:

   ```powershell
   $env:SPORT_REPORTER_API_KEY = 'local-test-key-change-before-hosting'
   ```

4. If you use local PostgreSQL, set its connection string:

   ```powershell
   $env:DATABASE_URL = 'postgresql://sport:local-dev-only@127.0.0.1:5432/sport_reporter'
   ```

5. If you use PostgreSQL, prepare the database with demo records:

   ```powershell
   uv run --python 3.13 python -m app.db migrate --seed-demo
   ```

6. Start the API:

   ```powershell
   uv run --python 3.13 python -m uvicorn app.main:app --reload
   ```

For memory mode, leave `DATABASE_URL` unset and omit steps 4 and 5. The backend
reads process environment variables. It does not load `.env`.

7. Open `http://127.0.0.1:8000/docs`.
8. Select **Authorize**.
9. Enter your API key in the bearer field.

## API reference

| Route | Result |
| --- | --- |
| `GET /health` | Public response with API status and storage source: `sample` or `postgresql` |
| `GET /ready` | Public response after a database schema check |
| `GET /upcoming?hours=24&leagues=lck,nba` | Matches with status `unstarted` in the next `hours` hours; allowed range: 1 to 168 |
| `GET /results?since=<ISO timestamp>&leagues=worlds` | Completed matches with an update time at or after `since` |
| `GET /matches/{id}` | One match, or HTTP 404 if the match does not exist |

Match routes require the header `Authorization: Bearer <SPORT_REPORTER_API_KEY>`.

League filters are optional. Separate league names with commas. Filters are not
case sensitive. Timestamps must include a UTC offset. This also applies to
`since`.

PostgreSQL list queries return a maximum of 100 records. Upcoming matches use
start time and ID for their order. Results use update time and ID. The API does
not support pagination.

For repeated result queries, use the match ID and update time to remove
duplicates. The `since` boundary includes records with that exact update time.
The current bot queries only when a user sends a command.

## Manage the database

These commands require `DATABASE_URL`:

| Command | Action |
| --- | --- |
| `python -m app.db migrate` | Apply each new SQL file from `app/migrations` once |
| `python -m app.db migrate --seed-demo` | Apply migrations and insert missing fictional demo records |
| `python -m app.db seed-demo --refresh` | Move timestamps for known demo records to the current demo period |

Normal application startup does not insert or reset records. A migration ledger
records each applied file. A database advisory lock prevents concurrent migration
runs from applying the same file. Each migration run uses a transaction.

Add a new numbered SQL file for each schema change. Do not change a migration
that the database has already applied. Enable Railway backups separately.

## Run tests

Run this command from the `backend` directory:

```powershell
uv run --python 3.13 pytest -q
```

API tests use demo records in memory. To run PostgreSQL integration tests, set
`TEST_DATABASE_URL` to a disposable local database connection string. These tests
create a unique temporary schema and remove it afterward. Without this variable,
the PostgreSQL tests do not run.
