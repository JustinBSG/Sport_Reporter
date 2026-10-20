"""FastAPI sample; replace the in-memory fixtures with a database repository."""

import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AwareDatetime, BaseModel


class MatchStatus(str, Enum):
    unstarted = "unstarted"
    in_progress = "inProgress"
    completed = "completed"


class Team(BaseModel):
    name: str
    code: str
    score: int | None = None


class Match(BaseModel):
    id: str
    sport: str
    league: str
    start_time_utc: AwareDatetime
    status: MatchStatus
    team1: Team
    team2: Team
    best_of: int
    stage: str
    updated_at: AwareDatetime


def sample_matches(now: datetime) -> list[Match]:
    """Fictional fixtures relative to startup, never a live schedule."""
    return [
        Match(
            id="lol-sample-upcoming", sport="lol", league="lck",
            start_time_utc=now + timedelta(hours=1),
            status=MatchStatus.unstarted,
            team1=Team(name="Sample Tigers", code="TIG"),
            team2=Team(name="Sample Dragons", code="DRG"),
            best_of=3, stage="Sample regular season", updated_at=now,
        ),
        Match(
            id="nba-sample-upcoming", sport="nba", league="nba",
            start_time_utc=now + timedelta(hours=3),
            status=MatchStatus.unstarted,
            team1=Team(name="Sample Stars", code="STR"),
            team2=Team(name="Sample Comets", code="COM"),
            best_of=1, stage="Sample regular season", updated_at=now,
        ),
        Match(
            id="lol-sample-result", sport="lol", league="worlds",
            start_time_utc=now - timedelta(hours=4),
            status=MatchStatus.completed,
            team1=Team(name="Sample Phoenix", code="PHX", score=3),
            team2=Team(name="Sample Wolves", code="WLV", score=1),
            best_of=5, stage="Sample knockout", updated_at=now - timedelta(hours=1),
        ),
    ]


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


def create_app(api_key: str | None = None, sample_time: datetime | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        token = api_key if api_key is not None else os.getenv("SPORT_REPORTER_API_KEY", "")
        if not token.strip():
            raise RuntimeError("Set SPORT_REPORTER_API_KEY before starting the API")
        application.state.api_key = token
        now = sample_time or datetime.now(timezone.utc)
        application.state.matches = sample_matches(now)
        yield

    application = FastAPI(
        title="Sport Reporter sample backend",
        description="Fictional, in-memory match data for client integration.",
        version="0.1.0", lifespan=lifespan,
    )

    def selected_matches(request: Request, leagues: str | None) -> list[Match]:
        selected = {slug.strip().lower() for slug in leagues.split(",") if slug.strip()} if leagues else set()
        return [match for match in request.app.state.matches if not selected or match.league in selected]

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "data_source": "sample"}

    @application.get("/upcoming", response_model=list[Match], dependencies=[Depends(authenticate)])
    def upcoming(
        request: Request,
        hours: Annotated[int, Query(ge=1, le=168)] = 24,
        leagues: str | None = None,
    ) -> list[Match]:
        now = sample_time or datetime.now(timezone.utc)
        end = now + timedelta(hours=hours)
        return sorted(
            (match for match in selected_matches(request, leagues)
             if match.status == MatchStatus.unstarted and now <= match.start_time_utc <= end),
            key=lambda match: match.start_time_utc,
        )

    @application.get("/results", response_model=list[Match], dependencies=[Depends(authenticate)])
    def results(
        request: Request,
        since: Annotated[AwareDatetime, Query(description="ISO 8601 timestamp including UTC offset")],
        leagues: str | None = None,
    ) -> list[Match]:
        return sorted(
            (match for match in selected_matches(request, leagues)
             if match.status == MatchStatus.completed and match.updated_at >= since),
            key=lambda match: match.updated_at,
        )

    @application.get("/matches/{match_id}", response_model=Match, dependencies=[Depends(authenticate)])
    def match_detail(match_id: str, request: Request) -> Match:
        for match in request.app.state.matches:
            if match.id == match_id:
                return match
        raise HTTPException(status_code=404, detail="Match not found")

    return application


app = create_app()
