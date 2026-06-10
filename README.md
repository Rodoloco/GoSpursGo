# GoSpursGo: NBA Data Pipeline + Spurs Dashboard

An end-to-end data engineering project: a Python pipeline that extracts
NBA statistics from the NBA Stats API, transforms them with pandas, and
loads them into a relational database with idempotent upserts, plus a
Streamlit dashboard that serves the data interactively.

Built and maintained by [Rodolfo Lopez](https://datawolf.ai), data
engineer and long-suffering Spurs fan.

## Architecture

```
            EXTRACT                TRANSFORM                LOAD
  NBA Stats API ──> pipeline/extract.py ──> pipeline/transform.py ──> pipeline/load.py
  (nba_api)         rate limiting,          snake_case columns,       explicit SQLAlchemy
                    retries w/ backoff      type casting, dedupe,     schema, idempotent
                                            derived fields            upserts (SQLite/Postgres)
                                                                            |
                                                                            v
                                                                  SERVE: spurs_analysis.py
                                                                  (Streamlit + Plotly)
```

- **`pipeline/extract.py`** wraps `nba_api` endpoints behind a shared
  rate limiter and retry-with-exponential-backoff helper. stats.nba.com
  throttles aggressive clients; every request waits its turn.
- **`pipeline/transform.py`** normalizes the raw ALL_CAPS frames:
  snake_case columns, real date types, deduplication on natural keys,
  and derived fields (home/away and opponent parsed from the matchup
  string). Output columns exactly match the load schema.
- **`pipeline/load.py`** defines the relational schema as SQLAlchemy
  models (`teams`, `rosters`, `team_game_logs`, `player_game_logs`,
  34 stat columns per player-game) and merges rows on natural primary
  keys. Re-running a season updates rows in place; it never duplicates.
- **`pipeline/run.py`** is the CLI entry point that orchestrates a full
  extract-transform-load pass per season.
- **`spurs_analysis.py`** is the serving layer: an interactive Streamlit
  dashboard with Plotly charts for season trends, box scores, shot
  charts, and play-by-play.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Load a season into SQLite (data/nba.db)
python -m pipeline.run --seasons 2025-26

# Load multiple seasons, or another team
python -m pipeline.run --seasons 2025-26 2024-25 --team SAS

# Point at Postgres instead of SQLite
python -m pipeline.run --seasons 2025-26 --db postgresql://user:pass@host/dbname

# Run the dashboard
streamlit run spurs_analysis.py
```

Then query away:

```sql
SELECT player_name,
       COUNT(*)            AS games,
       ROUND(AVG(pts), 1)  AS ppg,
       ROUND(AVG(reb), 1)  AS rpg
FROM player_game_logs
GROUP BY player_id
ORDER BY ppg DESC;
```

## Schema

| Table              | Grain                  | Primary key            |
| ------------------ | ---------------------- | ---------------------- |
| `teams`            | one row per team       | `id`                   |
| `rosters`          | player-team-season     | `team_id, season, player_id` |
| `team_game_logs`   | one row per team game  | `game_id, team_id`     |
| `player_game_logs` | one row per player game (34 stat columns) | `game_id, player_id` |

## Design decisions

- **Idempotent loads.** Upserts keyed on natural primary keys mean the
  pipeline can re-run any season safely: no duplicate rows, late stat
  corrections from the API update in place.
- **Explicit schema.** The models in `load.py` are the contract; the
  transform layer must produce exactly those columns. Type errors
  surface at load time, not in someone's dashboard three weeks later.
- **Polite extraction.** A fixed delay between requests plus retries
  with exponential backoff keeps the pipeline reliable against an API
  that rate-limits and occasionally times out.
- **Database-agnostic.** SQLite by default for zero-setup local runs;
  any SQLAlchemy URL (Postgres, etc.) via `--db` or `DATABASE_URL`.

## Roadmap

- Airflow DAG for scheduled season refreshes
- dbt models on top of the warehouse tables (season aggregates, rolling
  averages, opponent splits)
- Dashboard reads from the database instead of live API calls
