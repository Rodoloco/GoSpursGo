# Import necessary libraries
import streamlit as st  # For creating the web app interface
import pandas as pd  # For data manipulation and analysis
import plotly.express as px  # For creating interactive plots
from datetime import datetime  # For handling date and time
from nba_api.stats.static import teams  # To get team information from the NBA API
from nba_api.stats.endpoints import teamyearbyyearstats, leaguegamefinder, CommonTeamRoster  # To get specific stats from the NBA API

# --- Data Fetching Functions ---
# The @st.cache_data decorator caches the output of these functions, 
# so the app doesn't have to refetch the data from the API every time a user interacts with it.

@st.cache_data
def fetch_spurs_win_loss(last_n_years):
    """Fetches the San Antonio Spurs' win/loss record for the last N years."""
    try:
        # Find the Spurs team information, including their ID
        spurs = [team for team in teams.get_teams() if team['abbreviation'] == 'SAS'][0]
        spurs_id = spurs['id']
        # Fetch year-by-year stats for the Spurs
        stats = teamyearbyyearstats.TeamYearByYearStats(team_id=spurs_id).get_data_frames()[0]
        # Get the stats for the most recent N years
        recent_stats = stats.tail(last_n_years)
        return recent_stats[['YEAR', 'WINS', 'LOSSES']], None
    except Exception as e:
        # Return an empty DataFrame and the error message if something goes wrong
        return pd.DataFrame(), str(e)

@st.cache_data
def fetch_game_scores(season_start_date):
    """Fetches game-by-game scores and stats for the Spurs from a specified start date."""
    try:
        # Find the Spurs team information
        spurs = [team for team in teams.get_teams() if team['abbreviation'] == 'SAS'][0]
        spurs_id = spurs['id']
        # Find all games for the Spurs
        gamefinder = leaguegamefinder.LeagueGameFinder(team_id_nullable=spurs_id)
        games = gamefinder.get_data_frames()[0]
        # Convert date columns to datetime objects for proper comparison and plotting
        games['GAME_DATE'] = pd.to_datetime(games['GAME_DATE'])
        season_start_date = pd.to_datetime(season_start_date)
        # Filter for games that occurred on or after the selected season start date
        recent_games = games[games['GAME_DATE'] >= season_start_date].copy()
        # Extract and rename relevant columns for clarity
        recent_games['WIN_LOSS'] = recent_games['WL']
        recent_games['FG_PERCENTAGE'] = recent_games['FG_PCT']
        recent_games['THREE_POINT_PERCENTAGE'] = recent_games['FG3_PCT']
        # Return a sorted DataFrame with selected columns
        return recent_games[['GAME_DATE', 'PTS', 'MATCHUP', 'WIN_LOSS', 'FG_PERCENTAGE', 'THREE_POINT_PERCENTAGE','AST','REB']].sort_values('GAME_DATE'), None
    except Exception as e:
        return pd.DataFrame(), str(e)

# --- Visualization Functions ---

def visualize_shooting_stats(games_data):
    """Creates a scatter plot to visualize shooting percentages (FG% vs 3P%)."""
    try:
        # Determine if a game was Home or Away based on the 'MATCHUP' string
        games_data['HOME_AWAY'] = games_data['MATCHUP'].apply(lambda x: 'Home' if 'vs.' in x else 'Away')
        # Create the scatter plot using Plotly Express
        fig = px.scatter(games_data, x='FG_PERCENTAGE', y='THREE_POINT_PERCENTAGE', color='HOME_AWAY',
                         title='Field Goal vs Three-Point Percentages in Home vs Away Games (Current Season)',
                         labels={'HOME_AWAY': 'Home/Away', 'FG_PERCENTAGE': 'Field Goal %', 'THREE_POINT_PERCENTAGE': 'Three-Point %'},
                         hover_data=['MATCHUP', 'GAME_DATE'])
        return fig, None
    except Exception as e:
        return px.Figure(), str(e)

def visualize_win_loss_stats(win_loss_data):
    """Creates a bar chart to show win/loss records over several years."""
    try:
        # Create the bar chart using Plotly Express, grouping bars for Wins and Losses
        fig = px.bar(win_loss_data, x='YEAR', y=['WINS', 'LOSSES'], barmode='group',
                     title='Win/Loss Records Over the Years',
                     labels={'value': 'Number of Games', 'variable': 'Outcome', 'YEAR': 'Year'})
        return fig, None
    except Exception as e:
        return px.Figure(), str(e)

# --- Streamlit App Layout ---

# Set the title of the Streamlit app
st.title('San Antonio Spurs Analysis')

# --- Interactive Sidebar Elements ---
# Create a header for the settings section in the sidebar
st.sidebar.header('Settings')
# Add a date input widget to the sidebar to select the season start date
season_start_date = st.sidebar.date_input('Select Season Start Date', datetime(2023, 10, 23))
# Add a slider to the sidebar to select the number of years for win/loss records
selected_years = st.sidebar.slider('Select Number of Years for Win/Loss Records', 1, 10, 5)

# --- Data Fetching and Display ---

# Fetch game scores based on the selected start date
points_data, _ = fetch_game_scores(season_start_date)

# Proceed if the data was fetched successfully and is not empty
if not points_data.empty:
    # --- Key Metrics Calculation and Display ---
    # Calculate total wins, losses, and win percentage for the current season
    total_wins = points_data[points_data['WIN_LOSS'] == 'W'].shape[0]
    total_losses = points_data[points_data['WIN_LOSS'] == 'L'].shape[0]
    win_percentage = total_wins / (total_wins + total_losses) if total_wins + total_losses > 0 else 0

    # Calculate average points, assists, and rebounds
    avg_points = points_data['PTS'].mean()
    avg_assists = points_data['AST'].mean()
    avg_rebounds = points_data['REB'].mean()

    # Display the key metrics in columns for a clean layout
    st.header('Current Season Metrics')
    metrics_cols = st.columns(6)
    metrics_cols[0].metric("Total Wins", total_wins)
    metrics_cols[1].metric("Total Losses", total_losses)
    metrics_cols[2].metric("Win Percentage", f"{win_percentage:.1%}")
    metrics_cols[3].metric("Avg. Points", f"{avg_points:.2f}")
    metrics_cols[4].metric("Avg. Assists", f"{avg_assists:.2f}")
    metrics_cols[5].metric("Avg. Rebounds", f"{avg_rebounds:.2f}")

    # --- Visualizations for Current Season ---

    # Line Graph for Points Scored Per Game
    st.subheader('Points Scored Per Game (Current Season)')
    line_fig = px.line(points_data, x='GAME_DATE', y='PTS', 
                       title='Points Scored Per Game by the San Antonio Spurs',
                       labels={'GAME_DATE': 'Game Date', 'PTS': 'Points Scored'},
                       hover_data=['GAME_DATE', 'PTS', 'MATCHUP', 'WIN_LOSS'])
    line_fig.update_traces(mode='lines+markers') # Add markers to the line plot
    st.plotly_chart(line_fig, use_container_width=True)

    # Scatter Plot for Shooting Stats (Home vs. Away)
    st.subheader('Shooting Stats: Home vs Away')
    shooting_stats_fig, _ = visualize_shooting_stats(points_data)
    st.plotly_chart(shooting_stats_fig, use_container_width=True)

# --- Historical Win/Loss Records ---

# Fetch historical win/loss data based on the selected number of years
win_loss_data, _ = fetch_spurs_win_loss(selected_years)

if not win_loss_data.empty:
    # Bar Chart for Win/Loss Records Over the Years
    st.subheader('Win/Loss Records Over the Years')
    win_loss_fig, _ = visualize_win_loss_stats(win_loss_data)
    st.plotly_chart(win_loss_fig, use_container_width=True)
