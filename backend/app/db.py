"""Run migrations and optional demo seeding: python -m app.db --help."""

import argparse
import os
from datetime import datetime, timezone
from importlib.resources import files

import psycopg
from psycopg.types.json import Jsonb

from .models import sample_matches


def migrate(database_url: str) -> None:
    with psycopg.connect(database_url, connect_timeout=10) as connection:
        connection.execute("SELECT pg_advisory_xact_lock(817231902)")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        for migration in sorted(files("app").joinpath("migrations").iterdir(), key=lambda p: p.name):
            if not migration.name.endswith(".sql"):
                continue
            if connection.execute("SELECT 1 FROM schema_migrations WHERE name = %s", (migration.name,)).fetchone():
                continue
            connection.execute(migration.read_text(encoding="utf-8"), prepare=False)
            connection.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (migration.name,))
            print(f"Applied {migration.name}")
    print("Database migrations complete.")


def seed_demo(database_url: str, refresh: bool = False, now: datetime | None = None) -> None:
    conflict = (
        "DO UPDATE SET start_time_utc = EXCLUDED.start_time_utc, updated_at = EXCLUDED.updated_at "
        "WHERE matches.is_demo = TRUE"
        if refresh else "DO NOTHING"
    )
    with psycopg.connect(database_url, connect_timeout=10) as connection:
        for match in sample_matches(now or datetime.now(timezone.utc)):
            connection.execute(
                "INSERT INTO matches (id, sport, league, start_time_utc, status, team1, team2, "
                "best_of, stage, updated_at, is_demo) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                f"ON CONFLICT (id) {conflict}",
                (match.id, match.sport, match.league, match.start_time_utc, match.status.value,
                 Jsonb(match.team1.model_dump()), Jsonb(match.team2.model_dump()), match.best_of,
                 match.stage, match.updated_at, match.is_demo),
            )
    print("Fictional demo rows seeded. Existing rows kept unless --refresh was requested.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    migration = commands.add_parser("migrate", help="Apply pending SQL migrations")
    migration.add_argument("--seed-demo", action="store_true", help="Insert missing fictional demo rows")
    seed = commands.add_parser("seed-demo", help="Insert fictional fixtures after migrating")
    seed.add_argument("--refresh", action="store_true", help="Move only existing demo fixture times to now")
    args = parser.parse_args()
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        parser.error("Set DATABASE_URL before running database commands")
    if args.command == "migrate":
        migrate(database_url)
        if args.seed_demo:
            seed_demo(database_url)
    else:
        seed_demo(database_url, refresh=args.refresh)


if __name__ == "__main__":
    main()
