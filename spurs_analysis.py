import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from nba_api.stats.static import teams
from nba_api.stats.endpoints import (
    teamyearbyyearstats,
    leaguegamefinder,
    boxscoresummaryv2,
    boxscoretraditionalv2,
    boxscoreadvancedv2,
    playbyplayv2,
    shotchartdetail,
)

# Personal-Jesus palette
THEME = {
    "background": "#0c0c0e",
    "foreground": "#f0ede6",
    "primary": "#00b5ad",
    "primary_light": "#33c9c1",
    "accent": "#e5456e",
    "surface": "#141416",
    "border": "#252528",
    "muted": "#8a8a8f",
    "orange": "#f07920",
}

PLOT_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor=THEME["surface"],
        plot_bgcolor=THEME["surface"],
        font={"color": THEME["foreground"]},
        colorway=[THEME["primary"], THEME["accent"], THEME["orange"], THEME["primary_light"]],
        xaxis={
            "gridcolor": THEME["border"],
            "linecolor": THEME["muted"],
            "tickcolor": THEME["muted"],
        },
        yaxis={
            "gridcolor": THEME["border"],
            "linecolor": THEME["muted"],
            "tickcolor": THEME["muted"],
        },
        legend={"bgcolor": THEME["surface"], "bordercolor": THEME["border"]},
    )
)


def apply_theme(fig):
    fig.update_layout(template=PLOT_TEMPLATE)
    return fig


def style_app():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: linear-gradient(160deg, {THEME['background']} 0%, #111215 60%, #15161a 100%);
            color: {THEME['foreground']};
        }}
        [data-testid="stSidebar"] {{
            background: {THEME['surface']};
            border-right: 1px solid {THEME['border']};
        }}
        h1, h2, h3 {{
            color: {THEME['foreground']};
        }}
        .stMetric {{
            background: {THEME['surface']};
            border: 1px solid {THEME['border']};
            border-radius: 10px;
            padding: 0.5rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def get_spurs_team_id():
    spurs = [team for team in teams.get_teams() if team["abbreviation"] == "SAS"][0]
    return spurs["id"]


@st.cache_data
def fetch_spurs_win_loss(last_n_years):
    try:
        spurs_id = get_spurs_team_id()
        stats = teamyearbyyearstats.TeamYearByYearStats(team_id=spurs_id).get_data_frames()[0]
        recent_stats = stats.tail(last_n_years)
        return recent_stats[["YEAR", "WINS", "LOSSES"]], None
    except Exception as e:
        return pd.DataFrame(), str(e)


@st.cache_data
def fetch_game_scores(season_start_date, playoff_series_only=False, opponent_abbr="OKC"):
    try:
        spurs_id = get_spurs_team_id()
        if playoff_series_only:
            finder = leaguegamefinder.LeagueGameFinder(
                team_id_nullable=spurs_id,
                season_type_nullable="Playoffs",
            )
        else:
            finder = leaguegamefinder.LeagueGameFinder(team_id_nullable=spurs_id)

        games = finder.get_data_frames()[0]
        games["GAME_DATE"] = pd.to_datetime(games["GAME_DATE"])
        season_start_date = pd.to_datetime(season_start_date)

        if playoff_series_only:
            series_games = games[games["MATCHUP"].str.contains(opponent_abbr, case=False, na=False)].copy()
            if "SEASON_ID" in series_games.columns and not series_games.empty:
                latest_season = series_games["SEASON_ID"].max()
                series_games = series_games[series_games["SEASON_ID"] == latest_season].copy()
            recent_games = series_games
        else:
            recent_games = games[games["GAME_DATE"] >= season_start_date].copy()

        recent_games["WIN_LOSS"] = recent_games["WL"]
        recent_games["FG_PERCENTAGE"] = recent_games["FG_PCT"]
        recent_games["THREE_POINT_PERCENTAGE"] = recent_games["FG3_PCT"]
        recent_games["POINT_DIFF"] = recent_games["PLUS_MINUS"] if "PLUS_MINUS" in recent_games.columns else 0

        cols = [
            "GAME_ID",
            "GAME_DATE",
            "PTS",
            "MATCHUP",
            "WIN_LOSS",
            "FG_PERCENTAGE",
            "THREE_POINT_PERCENTAGE",
            "AST",
            "REB",
            "POINT_DIFF",
        ]
        return recent_games[cols].sort_values("GAME_DATE"), None
    except Exception as e:
        return pd.DataFrame(), str(e)


def _parse_minutes_to_float(min_str):
    if pd.isna(min_str):
        return 0.0
    if isinstance(min_str, (int, float)):
        return float(min_str)
    min_str = str(min_str)
    if ":" in min_str:
        parts = min_str.split(":")
        if len(parts) == 2:
            try:
                return float(parts[0]) + float(parts[1]) / 60.0
            except ValueError:
                return 0.0
    try:
        return float(min_str)
    except ValueError:
        return 0.0


def _parse_score_value(score_text):
    if pd.isna(score_text):
        return None
    if " - " not in str(score_text):
        return None
    left, right = str(score_text).split(" - ")
    try:
        return int(left), int(right)
    except ValueError:
        return None


@st.cache_data
def fetch_quarter_trends(game_ids):
    spurs_id = get_spurs_team_id()
    rows = []

    for game_id in game_ids:
        try:
            summary = boxscoresummaryv2.BoxScoreSummaryV2(game_id=game_id)
            line_score = summary.line_score.get_data_frame()
        except Exception:
            continue

        if line_score.empty:
            continue

        spurs_row = line_score[line_score["TEAM_ID"] == spurs_id]
        opp_row = line_score[line_score["TEAM_ID"] != spurs_id]
        if spurs_row.empty or opp_row.empty:
            continue

        spurs_row = spurs_row.iloc[0]
        opp_row = opp_row.iloc[0]

        for q in [1, 2, 3, 4]:
            rows.append(
                {
                    "GAME_ID": game_id,
                    "Quarter": f"Q{q}",
                    "Spurs_PTS": float(spurs_row.get(f"PTS_QTR{q}", 0) or 0),
                    "Opponent_PTS": float(opp_row.get(f"PTS_QTR{q}", 0) or 0),
                }
            )

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


@st.cache_data
def fetch_clutch_splits(game_ids):
    spurs_id = get_spurs_team_id()
    clutch_rows = []

    for game_id in game_ids:
        try:
            pbp = playbyplayv2.PlayByPlayV2(game_id=game_id).play_by_play.get_data_frame()
        except Exception:
            # nba_api can occasionally return non-standard payloads (missing resultSet).
            # Skip failed games so the dashboard still renders.
            continue

        if pbp.empty:
            continue

        pbp = pbp.sort_values("EVENTNUM").copy()
        pbp["SECONDS_LEFT"] = pbp["PCTIMESTRING"].apply(
            lambda x: int(str(x).split(":")[0]) * 60 + int(str(x).split(":")[1]) if isinstance(x, str) and ":" in x else 999
        )

        clutch_window = pbp[
            (pbp["PERIOD"] >= 4)
            & (pbp["SECONDS_LEFT"] <= 300)
            & (pbp["SCOREMARGIN"].astype(str).replace("TIE", "0").str.replace("+", "", regex=False).str.match(r"^-?\d+$", na=False))
            & (
                pbp["SCOREMARGIN"].astype(str).replace("TIE", "0").str.replace("+", "", regex=False).astype(int).abs()
                <= 5
            )
        ].copy()

        spurs_points = 0
        opp_points = 0
        prev_score = None

        for _, row in clutch_window.iterrows():
            cur_score = _parse_score_value(row.get("SCORE"))
            if cur_score is None:
                continue

            if prev_score is None:
                prev_score = cur_score
                continue

            score_delta = (cur_score[0] - prev_score[0]) + (cur_score[1] - prev_score[1])
            if score_delta <= 0:
                prev_score = cur_score
                continue

            scoring_team = row.get("PLAYER1_TEAM_ID")
            if pd.isna(scoring_team):
                prev_score = cur_score
                continue

            if int(scoring_team) == int(spurs_id):
                spurs_points += score_delta
            else:
                opp_points += score_delta

            prev_score = cur_score

        clutch_rows.append(
            {
                "GAME_ID": game_id,
                "Clutch_PTS_For": spurs_points,
                "Clutch_PTS_Against": opp_points,
                "Clutch_Net": spurs_points - opp_points,
            }
        )

    return pd.DataFrame(clutch_rows)


@st.cache_data
def fetch_player_series_stats(game_ids):
    spurs_id = get_spurs_team_id()
    all_rows = []

    for game_id in game_ids:
        try:
            trad = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id).player_stats.get_data_frame()
            adv = boxscoreadvancedv2.BoxScoreAdvancedV2(game_id=game_id).player_stats.get_data_frame()
        except Exception:
            continue

        trad = trad[trad["TEAM_ID"] == spurs_id].copy()
        adv = adv[adv["TEAM_ID"] == spurs_id].copy()
        if trad.empty:
            continue

        merge_cols = ["GAME_ID", "PLAYER_ID", "USG_PCT", "OFF_RATING", "DEF_RATING", "PIE"]
        adv = adv[[c for c in merge_cols if c in adv.columns]].copy()

        merged = trad.merge(adv, on=["GAME_ID", "PLAYER_ID"], how="left")
        merged["MIN_FLOAT"] = merged["MIN"].apply(_parse_minutes_to_float)
        all_rows.append(merged)

    if not all_rows:
        return pd.DataFrame()

    player_games = pd.concat(all_rows, ignore_index=True)

    agg = (
        player_games.groupby(["PLAYER_ID", "PLAYER_NAME"], as_index=False)
        .agg(
            GAMES=("GAME_ID", "nunique"),
            MIN=("MIN_FLOAT", "sum"),
            PTS=("PTS", "sum"),
            AST=("AST", "sum"),
            REB=("REB", "sum"),
            STL=("STL", "sum"),
            BLK=("BLK", "sum"),
            TOV=("TO", "sum"),
            FGM=("FGM", "sum"),
            FGA=("FGA", "sum"),
            FG3M=("FG3M", "sum"),
            FG3A=("FG3A", "sum"),
            FTM=("FTM", "sum"),
            FTA=("FTA", "sum"),
            PLUS_MINUS=("PLUS_MINUS", "sum"),
            USG_PCT=("USG_PCT", "mean"),
            OFF_RATING=("OFF_RATING", "mean"),
            DEF_RATING=("DEF_RATING", "mean"),
            PIE=("PIE", "mean"),
        )
        .fillna(0)
    )

    agg["PTS_PER_GAME"] = agg["PTS"] / agg["GAMES"]
    agg["AST_PER_GAME"] = agg["AST"] / agg["GAMES"]
    agg["REB_PER_GAME"] = agg["REB"] / agg["GAMES"]
    agg["EFG_PCT"] = ((agg["FGM"] + 0.5 * agg["FG3M"]) / agg["FGA"]).where(agg["FGA"] > 0, 0)
    agg["TS_PCT"] = (agg["PTS"] / (2 * (agg["FGA"] + 0.44 * agg["FTA"]))).where((agg["FGA"] + 0.44 * agg["FTA"]) > 0, 0)

    return agg.sort_values(["PTS", "MIN"], ascending=[False, False])


@st.cache_data
def fetch_last_game_shotchart(game_ids):
    if not game_ids:
        return pd.DataFrame(), None

    spurs_id = get_spurs_team_id()
    last_game_id = sorted(game_ids)[-1]

    try:
        chart = shotchartdetail.ShotChartDetail(
            team_id=spurs_id,
            player_id=0,
            game_id_nullable=last_game_id,
            context_measure_simple="FGA",
        )
        shots = chart.get_data_frames()[0]
        shots["SHOT_RESULT"] = shots["SHOT_MADE_FLAG"].map({1: "Made", 0: "Missed"})
        return shots, last_game_id
    except Exception:
        return pd.DataFrame(), last_game_id


def create_shot_chart_figure(shots_df):
    made = shots_df[shots_df["SHOT_MADE_FLAG"] == 1]
    missed = shots_df[shots_df["SHOT_MADE_FLAG"] == 0]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=made["LOC_X"],
            y=made["LOC_Y"],
            mode="markers",
            name="Made",
            marker={"size": 8, "color": THEME["primary"], "line": {"width": 0.5, "color": THEME["foreground"]}},
            hovertemplate="Made<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=missed["LOC_X"],
            y=missed["LOC_Y"],
            mode="markers",
            name="Missed",
            marker={"size": 8, "color": THEME["accent"], "symbol": "x"},
            hovertemplate="Missed<extra></extra>",
        )
    )

    court_shapes = [
        {"type": "circle", "x0": -7.5, "x1": 7.5, "y0": -7.5, "y1": 7.5, "line": {"color": THEME["foreground"], "width": 2}},
        {"type": "rect", "x0": -30, "x1": 30, "y0": -10, "y1": -7.5, "line": {"color": THEME["foreground"], "width": 2}},
        {"type": "rect", "x0": -80, "x1": 80, "y0": -47.5, "y1": 142.5, "line": {"color": THEME["foreground"], "width": 2}},
        {"type": "rect", "x0": -60, "x1": 60, "y0": -47.5, "y1": 142.5, "line": {"color": THEME["foreground"], "width": 2}},
        {"type": "circle", "x0": -60, "x1": 60, "y0": 82.5, "y1": 202.5, "line": {"color": THEME["foreground"], "width": 2}},
        {"type": "line", "x0": -220, "x1": -220, "y0": -47.5, "y1": 92.5, "line": {"color": THEME["foreground"], "width": 2}},
        {"type": "line", "x0": 220, "x1": 220, "y0": -47.5, "y1": 92.5, "line": {"color": THEME["foreground"], "width": 2}},
        {"type": "path", "path": "M -220 92.5 Q 0 300 220 92.5", "line": {"color": THEME["foreground"], "width": 2}},
    ]

    fig.update_layout(
        title="Last Game Shot Chart (Spurs)",
        xaxis={"showgrid": False, "zeroline": False, "visible": False, "range": [-250, 250]},
        yaxis={"showgrid": False, "zeroline": False, "visible": False, "range": [-60, 430], "scaleanchor": "x", "scaleratio": 1},
        shapes=court_shapes,
        showlegend=True,
        template=PLOT_TEMPLATE,
    )

    return fig


style_app()
st.title("San Antonio Spurs Deep Dive")
st.caption("Playoff analytics tuned for the OKC series.")

st.sidebar.header("Settings")
data_scope = st.sidebar.selectbox("Data Scope", ["Current Playoff Round vs OKC", "All Games Since Start Date"])
season_start_date = st.sidebar.date_input("Select Season Start Date", datetime(2023, 10, 23))
selected_years = st.sidebar.slider("Select Number of Years for Win/Loss Records", 1, 10, 5)

playoff_series_only = data_scope == "Current Playoff Round vs OKC"
points_data, points_error = fetch_game_scores(
    season_start_date,
    playoff_series_only=playoff_series_only,
    opponent_abbr="OKC",
)

if points_error:
    st.error(f"Error loading game data: {points_error}")

if not points_data.empty:
    game_ids = points_data["GAME_ID"].astype(str).tolist()

    total_wins = points_data[points_data["WIN_LOSS"] == "W"].shape[0]
    total_losses = points_data[points_data["WIN_LOSS"] == "L"].shape[0]
    win_percentage = total_wins / (total_wins + total_losses) if total_wins + total_losses > 0 else 0

    avg_points = points_data["PTS"].mean()
    avg_assists = points_data["AST"].mean()
    avg_rebounds = points_data["REB"].mean()

    metrics_title = "Playoff Round vs OKC Metrics" if playoff_series_only else "Current Season Metrics"
    st.header(metrics_title)
    metrics_cols = st.columns(6)
    metrics_cols[0].metric("Total Wins", total_wins)
    metrics_cols[1].metric("Total Losses", total_losses)
    metrics_cols[2].metric("Win %", f"{win_percentage:.1%}")
    metrics_cols[3].metric("Avg PTS", f"{avg_points:.2f}")
    metrics_cols[4].metric("Avg AST", f"{avg_assists:.2f}")
    metrics_cols[5].metric("Avg REB", f"{avg_rebounds:.2f}")

    st.subheader("Series Momentum")
    line_fig = px.line(
        points_data,
        x="GAME_DATE",
        y="PTS",
        title="Points Scored Per Game",
        hover_data=["GAME_DATE", "PTS", "MATCHUP", "WIN_LOSS"],
        markers=True,
        template=PLOT_TEMPLATE,
    )
    st.plotly_chart(apply_theme(line_fig), use_container_width=True)

    diff_fig = px.bar(
        points_data,
        x="GAME_DATE",
        y="POINT_DIFF",
        color="WIN_LOSS",
        color_discrete_map={"W": THEME["primary"], "L": THEME["accent"]},
        title="Point Differential by Game",
        template=PLOT_TEMPLATE,
    )
    st.plotly_chart(apply_theme(diff_fig), use_container_width=True)

    st.subheader("Quarter-by-Quarter Trends")
    quarter_df = fetch_quarter_trends(game_ids)
    if not quarter_df.empty:
        quarter_avg = quarter_df.groupby("Quarter", as_index=False)[["Spurs_PTS", "Opponent_PTS"]].mean()
        quarter_long = quarter_avg.melt(id_vars=["Quarter"], var_name="Team", value_name="Avg_PTS")
        quarter_long["Team"] = quarter_long["Team"].map({"Spurs_PTS": "Spurs", "Opponent_PTS": "OKC"})

        quarter_fig = px.bar(
            quarter_long,
            x="Quarter",
            y="Avg_PTS",
            color="Team",
            barmode="group",
            color_discrete_map={"Spurs": THEME["primary"], "OKC": THEME["accent"]},
            title="Average Points by Quarter",
            template=PLOT_TEMPLATE,
        )
        st.plotly_chart(apply_theme(quarter_fig), use_container_width=True)
    else:
        st.info("Quarter trend data is not available for the selected games.")

    st.subheader("Clutch-Time Splits (Last 5:00, score within 5)")
    clutch_df = fetch_clutch_splits(game_ids)
    if not clutch_df.empty:
        clutch_totals = clutch_df[["Clutch_PTS_For", "Clutch_PTS_Against"]].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Clutch PTS For", int(clutch_totals["Clutch_PTS_For"]))
        c2.metric("Clutch PTS Against", int(clutch_totals["Clutch_PTS_Against"]))
        c3.metric("Clutch Net", int(clutch_totals["Clutch_PTS_For"] - clutch_totals["Clutch_PTS_Against"]))

        clutch_game_fig = px.bar(
            clutch_df,
            x="GAME_ID",
            y="Clutch_Net",
            title="Clutch Net by Game",
            color="Clutch_Net",
            color_continuous_scale=[THEME["accent"], THEME["primary"]],
            template=PLOT_TEMPLATE,
        )
        st.plotly_chart(apply_theme(clutch_game_fig), use_container_width=True)
    else:
        st.info("No clutch scoring events found for the selected games.")

    st.subheader("Player-Level Series Stats (Usage + Efficiency + Plus/Minus)")
    player_df = fetch_player_series_stats(game_ids)
    if not player_df.empty:
        display_cols = [
            "PLAYER_NAME",
            "GAMES",
            "MIN",
            "PTS_PER_GAME",
            "AST_PER_GAME",
            "REB_PER_GAME",
            "USG_PCT",
            "EFG_PCT",
            "TS_PCT",
            "OFF_RATING",
            "DEF_RATING",
            "PLUS_MINUS",
        ]
        st.dataframe(
            player_df[display_cols].rename(columns={"PLAYER_NAME": "Player"}),
            use_container_width=True,
        )

        top_players = player_df.sort_values("PTS", ascending=False).head(10)
        usage_fig = px.scatter(
            top_players,
            x="USG_PCT",
            y="TS_PCT",
            size="MIN",
            color="PLUS_MINUS",
            color_continuous_scale=[THEME["accent"], THEME["primary"]],
            hover_name="PLAYER_NAME",
            title="Top Rotation: Usage vs True Shooting",
            template=PLOT_TEMPLATE,
        )
        st.plotly_chart(apply_theme(usage_fig), use_container_width=True)

    st.subheader("Last Game Shot Chart")
    shots_df, last_game_id = fetch_last_game_shotchart(game_ids)
    if not shots_df.empty:
        made = int(shots_df["SHOT_MADE_FLAG"].sum())
        attempts = int(shots_df.shape[0])
        st.caption(f"Game ID: {last_game_id} | Made/Attempted: {made}/{attempts}")
        shot_fig = create_shot_chart_figure(shots_df)
        st.plotly_chart(shot_fig, use_container_width=True)
    else:
        st.info("Shot chart data unavailable for the last game in this sample.")

    st.subheader("Series Data Exports")
    export_cols = st.columns(3)
    export_cols[0].download_button(
        label="Download Series Games CSV",
        data=points_data.to_csv(index=False),
        file_name="spurs_okc_series_games.csv",
        mime="text/csv",
    )
    export_cols[1].download_button(
        label="Download Player Series CSV",
        data=player_df.to_csv(index=False) if not player_df.empty else "",
        file_name="spurs_okc_player_series.csv",
        mime="text/csv",
    )
    export_cols[2].download_button(
        label="Download Clutch Splits CSV",
        data=clutch_df.to_csv(index=False) if not clutch_df.empty else "",
        file_name="spurs_okc_clutch_splits.csv",
        mime="text/csv",
    )

    st.subheader("Game-by-Game Breakdown")
    display_df = points_data.copy().sort_values("GAME_DATE", ascending=False)
    display_df["GAME_DATE"] = display_df["GAME_DATE"].dt.date
    st.dataframe(display_df, use_container_width=True)
else:
    st.warning("No game data found for the current filters.")

win_loss_data, _ = fetch_spurs_win_loss(selected_years)
if not win_loss_data.empty:
    st.subheader("Win/Loss Records Over the Years")
    win_loss_fig = px.bar(
        win_loss_data,
        x="YEAR",
        y=["WINS", "LOSSES"],
        barmode="group",
        color_discrete_sequence=[THEME["primary"], THEME["accent"]],
        template=PLOT_TEMPLATE,
    )
    st.plotly_chart(apply_theme(win_loss_fig), use_container_width=True)
