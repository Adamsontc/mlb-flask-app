from flask import Flask, render_template
from pybaseball import standings, team_batting, team_pitching
from datetime import datetime
import pandas as pd
import requests

app = Flask(__name__)

def get_mlb_odds(api_key):
    url = 'https://api.the-odds-api.com/v4/sports/baseball_mlb/odds'
    params = {
        'regions': 'us',
        'markets': 'h2h',
        'oddsFormat': 'american',
        'apiKey': api_key
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print("Error fetching odds:", response.status_code, response.text)
        return {}

    data = response.json()
    print("Raw odds data:", data[:2])  # Optional: for debugging

    odds_dict = {}

    for game in data:
        # 🧹 Filter by sport title just in case
        if game.get("sport_title") != "MLB":
            continue

        home = game['home_team']
        away = game['away_team']
        matchup = f"{away} @ {home}"

        if not game.get("bookmakers"):
            continue

        # Use the first bookmaker's odds
        for bookmaker in game["bookmakers"]:
            for market in bookmaker["markets"]:
                if market["key"] == "h2h":
                    outcomes = market["outcomes"]
                    odds_dict[matchup] = {
                        outcome["name"]: outcome["price"]
                        for outcome in outcomes
                    }
                    break
            if matchup in odds_dict:
                break  # Stop once we've added odds for this matchup

    return odds_dict

@app.route("/")
def home():
    return teams()  # Calls the function for `/teams`


@app.route("/teams")
def teams():
    year = datetime.now().year

    # Get standings
    try:
        standings_list = standings()
        divisions = ['AL East', 'AL Central', 'AL West', 'NL East', 'NL Central', 'NL West']
        standings_data = {
            div: df[['Tm', 'W', 'L', 'W-L%']]
            for div, df in zip(divisions, standings_list)
            
        }
    except Exception as e:
        print("Error loading standings:", e)
        standings_data = {}

    # Get team batting and pitching
    try:
        batting_stats = team_batting(year)[['Team', 'AVG', 'SLG', 'OBP', 'OPS']]
        pitching_stats = team_pitching(year)[['Team', 'ERA', 'WHIP']]
        combined_stats = pd.merge(batting_stats, pitching_stats, on='Team')
        combined_stats = combined_stats.sort_values('Team')
    except Exception as e:
        print("Error loading team stats:", e)
        combined_stats = pd.DataFrame()

    return render_template(
        "teams.html",
        standings=standings_data,
        stats=combined_stats.to_dict(orient='records')
    )

@app.route("/odds")
def odds():
    # Get betting odds
    api_key = 'dd300f06e45994df5e8a64d8fe82981c'
    odds_dict = get_mlb_odds(api_key)
    return render_template("odds.html", odds=odds_dict)

if __name__ == "__main__":
    app.run(debug=True)
