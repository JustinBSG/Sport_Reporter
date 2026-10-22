"""Authenticated match API with PostgreSQL or an explicit local sample mode."""

import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg import Error as DatabaseError
from psycopg_pool import PoolTimeout
from pydantic import AwareDatetime

from .models import Match, sample_matches
from .repository import MatchRepository, MemoryRepository, PostgresRepository

bearer = HTTPBearer(auto_error=False)


def authenticate(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> None:
    if credentials is None or not secrets.compare_digest(
        credentials.credentials.encode(), request.app.state.api_key.encode()
    ):
        raise HTTPException(
            status_code=401, detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_app(
    api_key: str | None = None,
    sample_time: datetime | None = None,
    repository: MatchRepository | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        token = api_key if api_key is not None else os.getenv("SPORT_REPORTER_API_KEY", "")
        if not token.strip():
            raise RuntimeError("Set SPORT_REPORTER_API_KEY before starting the API")
        application.state.api_key = token
        database_url = os.getenv("DATABASE_URL", "").strip()
        if repository is not None:
            store = repository
        elif database_url:
            store = PostgresRepository(database_url)
        else:
            if os.getenv("RAILWAY_ENVIRONMENT_ID"):
                raise RuntimeError("Set DATABASE_URL on Railway; refusing to use in-memory fixtures")
            store = MemoryRepository(sample_matches(sample_time or datetime.now(timezone.utc)))
        application.state.repository = store
        try:
            yield
        finally:
            store.close()

    application = FastAPI(
        title="Sport Reporter backend",
        description="Authenticated sports match API. Demo records have is_demo=true.",
        version="0.2.0", lifespan=lifespan,
    )

    def league_filter(leagues: str | None) -> list[str]:
        return sorted({slug.strip().lower() for slug in (leagues or "").split(",") if slug.strip()})

    @application.get("/health")
    def health(request: Request) -> dict[str, str]:
        return {"status": "ok", "data_source": request.app.state.repository.data_source}

    @application.get("/ready")
    def ready(request: Request) -> dict[str, str]:
        try:
            request.app.state.repository.check()
        except (DatabaseError, PoolTimeout):
            raise HTTPException(status_code=503, detail="Database unavailable") from None
        return {"status": "ready", "data_source": request.app.state.repository.data_source}

    @application.get("/upcoming", response_model=list[Match], dependencies=[Depends(authenticate)])
    def upcoming(
        request: Request,
        hours: Annotated[int, Query(ge=1, le=168)] = 24,
        leagues: str | None = None,
    ) -> list[Match]:
        now = sample_time or datetime.now(timezone.utc)
        return request.app.state.repository.upcoming(now, now + timedelta(hours=hours), league_filter(leagues))

    @application.get("/results", response_model=list[Match], dependencies=[Depends(authenticate)])
    def results(
        request: Request,
        since: Annotated[AwareDatetime, Query(description="ISO 8601 timestamp including UTC offset")],
        leagues: str | None = None,
    ) -> list[Match]:
        return request.app.state.repository.results(since, league_filter(leagues))

    @application.get("/matches/{match_id}", response_model=Match, dependencies=[Depends(authenticate)])
    def match_detail(match_id: str, request: Request) -> Match:
        match = request.app.state.repository.get(match_id)
        if match is None:
            raise HTTPException(status_code=404, detail="Match not found")
        return match

    return application


app = create_app()
