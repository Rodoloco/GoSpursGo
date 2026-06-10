"""Extraction layer: pulls raw data from the NBA Stats API.

Every request goes through a shared rate limiter and retry wrapper so
downstream layers only ever see complete DataFrames. stats.nba.com
throttles aggressive clients, so the delay between requests is not
optional.
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Optional

import pandas as pd
from nba_api.stats.endpoints import (
    commonteamroster,
    leaguegamefinder,
    playergamelogs,
)
from nba_api.stats.static import teams

logger = logging.getLogger(__name__)

REQUEST_DELAY_SECONDS = 0.8
REQUEST_TIMEOUT_SECONDS = 60
MAX_RETRIES = 3
BACKOFF_FACTOR = 2.0


def _fetch_frame(make_endpoint: Callable, description: str, frame_index: int = 0) -> pd.DataFrame:
    """Call an nba_api endpoint factory with rate limiting and
    exponential-backoff retries, returning one result DataFrame."""
    for attempt in range(1, MAX_RETRIES + 1):
        time.sleep(REQUEST_DELAY_SECONDS)
        try:
            frame = make_endpoint().get_data_frames()[frame_index]
            logger.info("%s: fetched %d rows", description, len(frame))
            return frame
        except Exception as exc:  # nba_api raises requests + JSON errors
            if attempt == MAX_RETRIES:
                logger.error("%s: giving up after %d attempts", description, attempt)
                raise
            wait = REQUEST_DELAY_SECONDS * (BACKOFF_FACTOR ** attempt)
            logger.warning(
                "%s failed (attempt %d/%d): %s; retrying in %.1fs",
                description, attempt, MAX_RETRIES, exc, wait,
            )
            time.sleep(wait)
    raise RuntimeError("unreachable")


def get_team(abbreviation: str = "SAS") -> dict:
    """Static team lookup (no API request)."""
    team = teams.find_team_by_abbreviation(abbreviation)
    if team is None:
        raise ValueError(f"No NBA team with abbreviation {abbreviation!r}")
    return team


def fetch_roster(team_id: int, season: str) -> pd.DataFrame:
    """Team roster for a season, e.g. season='2025-26'."""
    return _fetch_frame(
        lambda: commonteamroster.CommonTeamRoster(
            team_id=team_id, season=season, timeout=REQUEST_TIMEOUT_SECONDS
        ),
        f"roster {season}",
    )


def fetch_team_game_logs(team_id: int, season: str,
                         season_type: str = "Regular Season") -> pd.DataFrame:
    """One row per game from the team's perspective."""
    return _fetch_frame(
        lambda: leaguegamefinder.LeagueGameFinder(
            team_id_nullable=team_id,
            season_nullable=season,
            season_type_nullable=season_type,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ),
        f"team game logs {season}",
    )


def fetch_player_game_logs(team_id: int, season: str,
                           season_type: str = "Regular Season") -> pd.DataFrame:
    """One row per player per game; 30+ stat columns per row."""
    return _fetch_frame(
        lambda: playergamelogs.PlayerGameLogs(
            team_id_nullable=team_id,
            season_nullable=season,
            season_type_nullable=season_type,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ),
        f"player game logs {season}",
    )
