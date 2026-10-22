"""API models and explicitly fictional fixtures for deployment verification."""

from datetime import datetime, timedelta
from enum import Enum

from pydantic import AwareDatetime, BaseModel, Field


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
    best_of: int = Field(ge=1)
    stage: str
    updated_at: AwareDatetime
    is_demo: bool = False


def sample_matches(now: datetime) -> list[Match]:
    """Fictional fixtures; never present these as a live sports feed."""
    return [
        Match(
            id="lol-sample-upcoming", sport="lol", league="lck",
            start_time_utc=now + timedelta(hours=1), status=MatchStatus.unstarted,
            team1=Team(name="Sample Tigers", code="TIG"),
            team2=Team(name="Sample Dragons", code="DRG"),
            best_of=3, stage="Sample regular season", updated_at=now, is_demo=True,
        ),
        Match(
            id="nba-sample-upcoming", sport="nba", league="nba",
            start_time_utc=now + timedelta(hours=3), status=MatchStatus.unstarted,
            team1=Team(name="Sample Stars", code="STR"),
            team2=Team(name="Sample Comets", code="COM"),
            best_of=1, stage="Sample regular season", updated_at=now, is_demo=True,
        ),
        Match(
            id="lol-sample-result", sport="lol", league="worlds",
            start_time_utc=now - timedelta(hours=4), status=MatchStatus.completed,
            team1=Team(name="Sample Phoenix", code="PHX", score=3),
            team2=Team(name="Sample Wolves", code="WLV", score=1),
            best_of=5, stage="Sample knockout", updated_at=now - timedelta(hours=1), is_demo=True,
        ),
    ]
