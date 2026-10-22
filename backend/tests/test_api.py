from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


NOW = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
AUTH = {"Authorization": "Bearer test-token"}


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT_ID", raising=False)

@pytest.fixture
def client():
    with TestClient(create_app(api_key="test-token", sample_time=NOW)) as client:
        yield client


def test_health_is_public(client):
    assert client.get("/health").json() == {"status": "ok", "data_source": "sample"}


@pytest.mark.parametrize("path", ["/upcoming", "/results?since=2026-01-01T00:00:00Z", "/matches/lol-sample-upcoming"])
@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong"}, {"Authorization": "Basic wrong"}])
def test_match_endpoints_require_authentication(client, path, headers):
    response = client.get(path, headers=headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_upcoming_filters_window_and_leagues(client):
    matches = client.get("/upcoming", headers=AUTH).json()
    assert [match["league"] for match in matches] == ["lck", "nba"]
    assert all(match["status"] == "unstarted" for match in matches)
    assert len(client.get("/upcoming?hours=2", headers=AUTH).json()) == 1
    assert client.get("/upcoming?leagues=NBA,worlds", headers=AUTH).json()[0]["league"] == "nba"
    assert client.get("/upcoming?leagues=unknown", headers=AUTH).json() == []


@pytest.mark.parametrize("hours", [0, -1, 169, "invalid"])
def test_invalid_window(client, hours):
    assert client.get("/upcoming", params={"hours": hours}, headers=AUTH).status_code == 422


def test_results_filter_by_update_time_and_league(client):
    response = client.get("/results", params={"since": "2026-01-01T11:00:00Z", "leagues": "worlds"}, headers=AUTH)
    assert response.status_code == 200
    assert response.json()[0]["team1"]["score"] == 3
    assert client.get("/results", params={"since": "2026-01-01T12:00:00Z"}, headers=AUTH).json() == []
    assert client.get("/results", params={"since": "2026-01-01T00:00:00Z", "leagues": "nba"}, headers=AUTH).json() == []


@pytest.mark.parametrize("since", [None, "invalid", "2026-01-01T00:00:00"])
def test_results_require_timezone_aware_since(client, since):
    params = {} if since is None else {"since": since}
    assert client.get("/results", params=params, headers=AUTH).status_code == 422


def test_match_lookup_and_missing_id(client):
    response = client.get("/matches/lol-sample-upcoming", headers=AUTH)
    assert response.status_code == 200
    assert response.json()["id"] == "lol-sample-upcoming"
    assert client.get("/matches/missing", headers=AUTH).status_code == 404


def test_missing_key_prevents_startup(monkeypatch):
    monkeypatch.delenv("SPORT_REPORTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SPORT_REPORTER_API_KEY"):
        with TestClient(create_app()):
            pass


def test_key_can_be_configured_through_environment(monkeypatch):
    monkeypatch.setenv("SPORT_REPORTER_API_KEY", "from-environment")
    with TestClient(create_app(sample_time=NOW)) as client:
        assert client.get("/upcoming", headers={"Authorization": "Bearer from-environment"}).status_code == 200


def test_railway_requires_persistent_database(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "test-environment")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        with TestClient(create_app(api_key="test-token")):
            pass


def test_readiness_reports_database_failure():
    from psycopg import OperationalError
    from app.repository import MemoryRepository

    class BrokenRepository(MemoryRepository):
        def check(self):
            raise OperationalError("private connection details")

    with TestClient(create_app(api_key="test-token", repository=BrokenRepository([]))) as client:
        assert client.get("/health").status_code == 200
        response = client.get("/ready")
        assert response.status_code == 503
        assert "private" not in response.text
