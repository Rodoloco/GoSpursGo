"""Pipeline entry point: extract -> transform -> load for one or more
seasons.

    python -m pipeline.run --seasons 2025-26 2024-25
    python -m pipeline.run --seasons 2025-26 --db postgresql://...

Re-running a season is safe: loads are idempotent upserts.
"""
from __future__ import annotations

import argparse
import logging
import os
import pathlib

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from pipeline import extract, transform
from pipeline.load import (
    Base,
    DEFAULT_DATABASE_URL,
    PlayerGameLog,
    RosterEntry,
    Team,
    TeamGameLog,
    upsert_dataframe,
)

logger = logging.getLogger(__name__)


def run(seasons, database_url=DEFAULT_DATABASE_URL, team_abbreviation="SAS"):
    if database_url.startswith("sqlite:///"):
        pathlib.Path(database_url.replace("sqlite:///", "")).parent.mkdir(
            parents=True, exist_ok=True
        )
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    team = extract.get_team(team_abbreviation)
    logger.info("Pipeline start: %s, seasons %s", team["full_name"], ", ".join(seasons))

    with Session(engine) as session:
        session.merge(Team(
            id=team["id"],
            full_name=team["full_name"],
            abbreviation=team["abbreviation"],
            nickname=team.get("nickname"),
            city=team.get("city"),
            state=team.get("state"),
            year_founded=team.get("year_founded"),
        ))

        for season in seasons:
            roster = transform.transform_roster(
                extract.fetch_roster(team["id"], season), season
            )
            upsert_dataframe(session, RosterEntry, roster)

            team_logs = transform.transform_team_game_logs(
                extract.fetch_team_game_logs(team["id"], season)
            )
            upsert_dataframe(session, TeamGameLog, team_logs)

            player_logs = transform.transform_player_game_logs(
                extract.fetch_player_game_logs(team["id"], season)
            )
            upsert_dataframe(session, PlayerGameLog, player_logs)

        session.commit()
    logger.info("Pipeline complete")


def main():
    parser = argparse.ArgumentParser(description="NBA data pipeline")
    parser.add_argument("--seasons", nargs="+", required=True,
                        metavar="YYYY-YY", help="e.g. 2025-26 2024-25")
    parser.add_argument("--db", default=os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL),
                        help="SQLAlchemy database URL (default: local SQLite)")
    parser.add_argument("--team", default="SAS",
                        help="Team abbreviation (default: SAS)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run(args.seasons, database_url=args.db, team_abbreviation=args.team)


if __name__ == "__main__":
    main()
