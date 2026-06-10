"""Load layer: explicit relational schema plus idempotent upserts.

Models define the contract the transform layer must meet. Upserts go
through SQLAlchemy's merge() keyed on natural primary keys, so re-running
the pipeline for a season updates rows in place instead of duplicating
them. SQLite by default; any SQLAlchemy URL (e.g. Postgres) works.
"""
from __future__ import annotations

import logging

import pandas as pd
from sqlalchemy import Date, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

logger = logging.getLogger(__name__)

DEFAULT_DATABASE_URL = "sqlite:///data/nba.db"


class Base(DeclarativeBase):
    pass


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String)
    abbreviation: Mapped[str] = mapped_column(String)
    nickname: Mapped[str] = mapped_column(String, nullable=True)
    city: Mapped[str] = mapped_column(String, nullable=True)
    state: Mapped[str] = mapped_column(String, nullable=True)
    year_founded: Mapped[int] = mapped_column(Integer, nullable=True)


class RosterEntry(Base):
    __tablename__ = "rosters"

    team_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season: Mapped[str] = mapped_column(String, primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player: Mapped[str] = mapped_column(String)
    jersey_number: Mapped[str] = mapped_column(String, nullable=True)
    position: Mapped[str] = mapped_column(String, nullable=True)
    height: Mapped[str] = mapped_column(String, nullable=True)
    weight: Mapped[str] = mapped_column(String, nullable=True)
    birth_date: Mapped[str] = mapped_column(String, nullable=True)
    age: Mapped[float] = mapped_column(Float, nullable=True)
    experience: Mapped[str] = mapped_column(String, nullable=True)
    school: Mapped[str] = mapped_column(String, nullable=True)
    how_acquired: Mapped[str] = mapped_column(String, nullable=True)


class TeamGameLog(Base):
    __tablename__ = "team_game_logs"

    game_id: Mapped[str] = mapped_column(String, primary_key=True)
    team_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[str] = mapped_column(String)
    team_abbreviation: Mapped[str] = mapped_column(String)
    team_name: Mapped[str] = mapped_column(String)
    game_date = mapped_column(Date)
    matchup: Mapped[str] = mapped_column(String)
    wl: Mapped[str] = mapped_column(String, nullable=True)
    is_home: Mapped[bool] = mapped_column(Integer)
    opponent: Mapped[str] = mapped_column(String, nullable=True)
    min: Mapped[float] = mapped_column(Float, nullable=True)
    pts: Mapped[int] = mapped_column(Integer, nullable=True)
    fgm: Mapped[int] = mapped_column(Integer, nullable=True)
    fga: Mapped[int] = mapped_column(Integer, nullable=True)
    fg_pct: Mapped[float] = mapped_column(Float, nullable=True)
    fg3m: Mapped[int] = mapped_column(Integer, nullable=True)
    fg3a: Mapped[int] = mapped_column(Integer, nullable=True)
    fg3_pct: Mapped[float] = mapped_column(Float, nullable=True)
    ftm: Mapped[int] = mapped_column(Integer, nullable=True)
    fta: Mapped[int] = mapped_column(Integer, nullable=True)
    ft_pct: Mapped[float] = mapped_column(Float, nullable=True)
    oreb: Mapped[int] = mapped_column(Integer, nullable=True)
    dreb: Mapped[int] = mapped_column(Integer, nullable=True)
    reb: Mapped[int] = mapped_column(Integer, nullable=True)
    ast: Mapped[int] = mapped_column(Integer, nullable=True)
    stl: Mapped[int] = mapped_column(Integer, nullable=True)
    blk: Mapped[int] = mapped_column(Integer, nullable=True)
    tov: Mapped[int] = mapped_column(Integer, nullable=True)
    pf: Mapped[int] = mapped_column(Integer, nullable=True)
    plus_minus: Mapped[float] = mapped_column(Float, nullable=True)


class PlayerGameLog(Base):
    __tablename__ = "player_game_logs"

    game_id: Mapped[str] = mapped_column(String, primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_year: Mapped[str] = mapped_column(String)
    player_name: Mapped[str] = mapped_column(String)
    team_id: Mapped[int] = mapped_column(Integer)
    team_abbreviation: Mapped[str] = mapped_column(String)
    game_date = mapped_column(Date)
    matchup: Mapped[str] = mapped_column(String)
    wl: Mapped[str] = mapped_column(String, nullable=True)
    min: Mapped[float] = mapped_column(Float, nullable=True)
    fgm: Mapped[int] = mapped_column(Integer, nullable=True)
    fga: Mapped[int] = mapped_column(Integer, nullable=True)
    fg_pct: Mapped[float] = mapped_column(Float, nullable=True)
    fg3m: Mapped[int] = mapped_column(Integer, nullable=True)
    fg3a: Mapped[int] = mapped_column(Integer, nullable=True)
    fg3_pct: Mapped[float] = mapped_column(Float, nullable=True)
    ftm: Mapped[int] = mapped_column(Integer, nullable=True)
    fta: Mapped[int] = mapped_column(Integer, nullable=True)
    ft_pct: Mapped[float] = mapped_column(Float, nullable=True)
    oreb: Mapped[int] = mapped_column(Integer, nullable=True)
    dreb: Mapped[int] = mapped_column(Integer, nullable=True)
    reb: Mapped[int] = mapped_column(Integer, nullable=True)
    ast: Mapped[int] = mapped_column(Integer, nullable=True)
    tov: Mapped[int] = mapped_column(Integer, nullable=True)
    stl: Mapped[int] = mapped_column(Integer, nullable=True)
    blk: Mapped[int] = mapped_column(Integer, nullable=True)
    blka: Mapped[int] = mapped_column(Integer, nullable=True)
    pf: Mapped[int] = mapped_column(Integer, nullable=True)
    pfd: Mapped[int] = mapped_column(Integer, nullable=True)
    pts: Mapped[int] = mapped_column(Integer, nullable=True)
    plus_minus: Mapped[float] = mapped_column(Float, nullable=True)
    nba_fantasy_pts: Mapped[float] = mapped_column(Float, nullable=True)
    dd2: Mapped[int] = mapped_column(Integer, nullable=True)
    td3: Mapped[int] = mapped_column(Integer, nullable=True)


def upsert_dataframe(session: Session, model: type, frame: pd.DataFrame) -> int:
    """Merge every row of `frame` into `model`'s table, keyed on the
    model's primary key. Returns the number of rows merged."""
    columns = model.__table__.columns.keys()
    aligned = frame[[c for c in frame.columns if c in columns]]
    # NaN/NaT are pandas concepts; the database needs NULL.
    aligned = aligned.astype(object).where(pd.notna(aligned), None)
    records = aligned.to_dict("records")
    for record in records:
        session.merge(model(**record))
    logger.info("%s: merged %d rows", model.__tablename__, len(records))
    return len(records)
