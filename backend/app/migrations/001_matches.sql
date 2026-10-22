CREATE TABLE matches (
    id TEXT PRIMARY KEY,
    sport TEXT NOT NULL,
    league TEXT NOT NULL CHECK (league = lower(league)),
    start_time_utc TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('unstarted', 'inProgress', 'completed')),
    team1 JSONB NOT NULL,
    team2 JSONB NOT NULL,
    best_of INTEGER NOT NULL CHECK (best_of >= 1),
    stage TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    is_demo BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX matches_upcoming_idx ON matches (start_time_utc) WHERE status = 'unstarted';
CREATE INDEX matches_results_idx ON matches (updated_at) WHERE status = 'completed';
CREATE INDEX matches_league_idx ON matches (league);
