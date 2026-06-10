"""Transformation layer: normalize raw API frames into clean,
schema-aligned tables.

The NBA Stats API returns ALL_CAPS columns, stringly-typed dates, and
occasional duplicate rows. Each function here takes the raw frame from
extract.py and returns a frame whose columns exactly match one of the
load.py models.
"""
from __future__ import annotations

import pandas as pd

# Player game log stat columns kept from the PlayerGameLogs endpoint
# (rank columns are dropped). 30+ stats per player per game.
PLAYER_LOG_COLUMNS = [
    "season_year", "player_id", "player_name", "team_id",
    "team_abbreviation", "game_id", "game_date", "matchup", "wl", "min",
    "fgm", "fga", "fg_pct", "fg3m", "fg3a", "fg3_pct", "ftm", "fta",
    "ft_pct", "oreb", "dreb", "reb", "ast", "tov", "stl", "blk", "blka",
    "pf", "pfd", "pts", "plus_minus", "nba_fantasy_pts", "dd2", "td3",
]

TEAM_LOG_COLUMNS = [
    "season_id", "team_id", "team_abbreviation", "team_name", "game_id",
    "game_date", "matchup", "wl", "min", "pts", "fgm", "fga", "fg_pct",
    "fg3m", "fg3a", "fg3_pct", "ftm", "fta", "ft_pct", "oreb", "dreb",
    "reb", "ast", "stl", "blk", "tov", "pf", "plus_minus",
    "is_home", "opponent",
]

ROSTER_COLUMNS = [
    "team_id", "season", "player_id", "player", "jersey_number",
    "position", "height", "weight", "birth_date", "age", "experience",
    "school", "how_acquired",
]


def _snake_case_columns(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.rename(columns={c: c.lower() for c in frame.columns})


def _parse_matchup(frame: pd.DataFrame) -> pd.DataFrame:
    """Derive is_home and opponent from MATCHUP ('SAS vs. DEN' = home,
    'SAS @ DEN' = away)."""
    frame["is_home"] = ~frame["matchup"].str.contains("@", na=False)
    frame["opponent"] = frame["matchup"].str.extract(r"(?:vs\.|@)\s*(\w+)$")
    return frame


def transform_player_game_logs(raw: pd.DataFrame) -> pd.DataFrame:
    frame = _snake_case_columns(raw)
    frame["game_date"] = pd.to_datetime(frame["game_date"]).dt.date
    frame = frame.drop_duplicates(subset=["game_id", "player_id"], keep="last")
    return frame[PLAYER_LOG_COLUMNS]


def transform_team_game_logs(raw: pd.DataFrame) -> pd.DataFrame:
    frame = _snake_case_columns(raw)
    frame["game_date"] = pd.to_datetime(frame["game_date"]).dt.date
    frame = _parse_matchup(frame)
    frame = frame.drop_duplicates(subset=["game_id", "team_id"], keep="last")
    return frame[TEAM_LOG_COLUMNS]


def transform_roster(raw: pd.DataFrame, season: str) -> pd.DataFrame:
    frame = _snake_case_columns(raw)
    frame = frame.rename(columns={
        "teamid": "team_id",
        "num": "jersey_number",
        "exp": "experience",
    })
    frame["season"] = season
    frame["age"] = pd.to_numeric(frame["age"], errors="coerce")
    frame = frame.drop_duplicates(subset=["team_id", "season", "player_id"], keep="last")
    return frame[ROSTER_COLUMNS]
