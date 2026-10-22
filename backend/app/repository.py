"""Small repositories sharing the same API contract."""

from datetime import datetime
from typing import Protocol

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .models import Match, MatchStatus


class MatchRepository(Protocol):
    data_source: str

    def upcoming(self, now: datetime, end: datetime, leagues: list[str]) -> list[Match]: ...
    def results(self, since: datetime, leagues: list[str]) -> list[Match]: ...
    def get(self, match_id: str) -> Match | None: ...
    def check(self) -> None: ...
    def close(self) -> None: ...


class MemoryRepository:
    data_source = "sample"

    def __init__(self, matches: list[Match]):
        self.matches = matches

    def upcoming(self, now: datetime, end: datetime, leagues: list[str]) -> list[Match]:
        return sorted(
            (m for m in self.matches if m.status == MatchStatus.unstarted
             and now <= m.start_time_utc <= end and (not leagues or m.league in leagues)),
            key=lambda m: m.start_time_utc,
        )

    def results(self, since: datetime, leagues: list[str]) -> list[Match]:
        return sorted(
            (m for m in self.matches if m.status == MatchStatus.completed
             and m.updated_at >= since and (not leagues or m.league in leagues)),
            key=lambda m: m.updated_at,
        )

    def get(self, match_id: str) -> Match | None:
        return next((m for m in self.matches if m.id == match_id), None)

    def check(self) -> None:
        pass

    def close(self) -> None:
        pass


class PostgresRepository:
    data_source = "postgresql"

    def __init__(self, database_url: str):
        self.pool = ConnectionPool(
            database_url, min_size=1, max_size=5, timeout=5,
            kwargs={"row_factory": dict_row, "connect_timeout": 5},
            check=ConnectionPool.check_connection, open=False,
        )
        self.pool.open()
        try:
            self.pool.wait(timeout=15)
            self.check()
        except Exception:
            self.pool.close()
            raise

    def _query(self, query: str, params: tuple) -> list[Match]:
        with self.pool.connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [Match.model_validate(row) for row in rows]

    def upcoming(self, now: datetime, end: datetime, leagues: list[str]) -> list[Match]:
        return self._query(
            "SELECT * FROM matches WHERE status = 'unstarted' "
            "AND start_time_utc BETWEEN %s AND %s "
            "AND (cardinality(%s::text[]) = 0 OR league = ANY(%s::text[])) "
            "ORDER BY start_time_utc, id LIMIT 100",
            (now, end, leagues, leagues),
        )

    def results(self, since: datetime, leagues: list[str]) -> list[Match]:
        return self._query(
            "SELECT * FROM matches WHERE status = 'completed' AND updated_at >= %s "
            "AND (cardinality(%s::text[]) = 0 OR league = ANY(%s::text[])) "
            "ORDER BY updated_at, id LIMIT 100",
            (since, leagues, leagues),
        )

    def get(self, match_id: str) -> Match | None:
        matches = self._query("SELECT * FROM matches WHERE id = %s", (match_id,))
        return matches[0] if matches else None

    def check(self) -> None:
        with self.pool.connection() as connection:
            connection.execute("SELECT id FROM matches LIMIT 0")

    def close(self) -> None:
        self.pool.close()
