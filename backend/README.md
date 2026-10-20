# Sport Reporter backend

A Python 3.11+ FastAPI starter for LoL and future multi-sport notification clients.
All matches are **fictional sample data**, stored in memory and recreated relative
to each server start. There is no live extraction, persistence, or notification delivery yet.

## Run locally (PowerShell)

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:SPORT_REPORTER_API_KEY = "replace-with-a-long-random-token"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs and use **Authorize** with your token.
`.env.example` documents configuration; `.env` files are not loaded automatically.
The process refuses to start without an API key. Keep real tokens out of Git.

```powershell
$headers = @{ Authorization = "Bearer $env:SPORT_REPORTER_API_KEY" }
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod "http://127.0.0.1:8000/upcoming?leagues=lck,nba&hours=24" -Headers $headers
$since = [Uri]::EscapeDataString([DateTimeOffset]::UtcNow.AddHours(-24).ToString("o"))
Invoke-RestMethod "http://127.0.0.1:8000/results?since=$since&leagues=worlds" -Headers $headers
Invoke-RestMethod http://127.0.0.1:8000/matches/lol-sample-upcoming -Headers $headers
```

## API

| Route | Behavior |
| --- | --- |
| `GET /health` | Public liveness and explicit sample-data marker |
| `GET /upcoming?hours=24&leagues=lck,nba` | Unstarted matches within the next 1-168 hours, sorted by start |
| `GET /results?since=<ISO timestamp>&leagues=worlds` | Completed matches updated at or after `since`, sorted by update time |
| `GET /matches/{id}` | One match, or HTTP 404 |

Match routes require `Authorization: Bearer <SPORT_REPORTER_API_KEY>`.
League filters are optional, comma separated, and case insensitive. Unknown leagues
return an empty list. Timestamps include a UTC offset; `since` must include a timezone.
Results use `updated_at` so clients can poll for newly completed or corrected results.
Sample statuses and scores remain fixed until the process restarts; expired upcoming
fixtures drop out of the time window. Clients should deduplicate polling results by ID
and update time because the `since` boundary is inclusive.

## Test

Run from the `backend` directory:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Next steps from the project guide: replace `sample_matches` with PostgreSQL-backed
league/match repositories, implement idempotent source extractors, and add a persistent
notification log before wiring Discord or Grok delivery. Use HTTPS when hosting the API.
