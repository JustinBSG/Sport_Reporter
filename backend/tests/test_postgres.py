"""Real PostgreSQL checks. Set TEST_DATABASE_URL to a disposable test server."""

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.conninfo import make_conninfo

from app.db import migrate, seed_demo
from app.main import create_app
from app.repository import PostgresRepository

NOW = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
AUTH = {"Authorization": "Bearer test-token"}


@pytest.fixture
def database_url():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to run real PostgreSQL integration tests")
    schema = "test_" + uuid4().hex
    with psycopg.connect(url, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    try:
        yield make_conninfo(url, options=f"-csearch_path={schema}")
    finally:
        with psycopg.connect(url, autocommit=True) as connection:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def test_database_survives_reconnect_and_migrations_are_repeatable(database_url):
    migrate(database_url)
    migrate(database_url)
    seed_demo(database_url, now=NOW)
    seed_demo(database_url, now=NOW + timedelta(days=1))
    for _ in range(2):
        with TestClient(create_app("test-token", NOW, PostgresRepository(database_url))) as client:
            assert client.get("/ready").json()["data_source"] == "postgresql"
            matches = client.get("/upcoming?leagues=LCK", headers=AUTH).json()
            assert [m["id"] for m in matches] == ["lol-sample-upcoming"]
            assert matches[0]["is_demo"] is True
            assert client.get("/upcoming?hours=2", headers=AUTH).json() == matches
            assert len(client.get("/upcoming", headers=AUTH).json()) == 2
            assert client.get("/upcoming?leagues=unknown", headers=AUTH).json() == []
            results = client.get("/results?since=2026-01-01T11:00:00Z", headers=AUTH).json()
            assert results[0]["team1"]["score"] == 3
            assert client.get("/matches/lol-sample-result", headers=AUTH).status_code == 200
            assert client.get("/matches/missing", headers=AUTH).status_code == 404
            assert client.get("/upcoming").status_code == 401
    with psycopg.connect(database_url) as connection:
        assert connection.execute("SELECT count(*) FROM matches").fetchone()[0] == 3
        assert connection.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 1


def test_refresh_only_moves_demo_rows(database_url):
    migrate(database_url)
    seed_demo(database_url, now=NOW)
    with psycopg.connect(database_url) as connection:
        connection.execute("UPDATE matches SET is_demo = FALSE WHERE id = 'nba-sample-upcoming'")
    seed_demo(database_url, refresh=True, now=NOW + timedelta(days=1))
    repository = PostgresRepository(database_url)
    try:
        assert repository.get("lol-sample-upcoming").updated_at == NOW + timedelta(days=1)
        assert repository.get("nba-sample-upcoming").updated_at == NOW
    finally:
        repository.close()
