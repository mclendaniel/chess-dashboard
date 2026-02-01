#!/usr/bin/env python3
"""
Chess Dashboard Generator
Fetches chess.com data and generates a GitHub README dashboard.
"""

import json
import os
import requests
from datetime import datetime
from collections import defaultdict
import anthropic

USERNAME = "skilletobviously"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

HEADERS = {"User-Agent": "Chess Dashboard Generator"}


def fetch_player_stats(username):
    """Fetch player statistics."""
    url = f"https://api.chess.com/pub/player/{username}/stats"
    response = requests.get(url, headers=HEADERS)
    return response.json() if response.status_code == 200 else {}


def fetch_games(username):
    """Fetch all games for a player."""
    import time
    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
    response = requests.get(archives_url, headers=HEADERS)
    if response.status_code != 200:
        return []

    archives = response.json().get("archives", [])
    all_games = []

    for archive_url in archives:
        time.sleep(0.5)
        response = requests.get(archive_url, headers=HEADERS)
        if response.status_code == 200:
            games = response.json().get("games", [])
            all_games.extend(games)

    return all_games


def get_rating_history(games, username):
    """Extract rating history from games."""
    history = []
    for game in sorted(games, key=lambda g: g.get("end_time", 0)):
        is_white = game["white"]["username"].lower() == username.lower()
        player = game["white"] if is_white else game["black"]
        end_time = game.get("end_time", 0)
        if end_time:
            date = datetime.fromtimestamp(end_time).strftime("%Y-%m-%d")
            history.append({"date": date, "rating": player["rating"]})
    return history


def generate_elo_chart(rating_history):
    """Generate ASCII/text ELO chart for README."""
    if not rating_history:
        return "No rating data available."

    # Get last 30 data points
    recent = rating_history[-30:]
    ratings = [r["rating"] for r in recent]

    min_r = min(ratings)
    max_r = max(ratings)
    range_r = max_r - min_r or 1

    # Create sparkline-style chart
    chart_chars = "▁▂▃▄▅▆▇█"
    sparkline = ""
    for r in ratings:
        idx = int((r - min_r) / range_r * (len(chart_chars) - 1))
        sparkline += chart_chars[idx]

    current = ratings[-1]
    start = ratings[0]
    change = current - start

    chart = f"""
```
Rating: {current} ({'+' if change >= 0 else ''}{change} over last {len(recent)} games)

{sparkline}
Low: {min_r}  High: {max_r}
```
"""
    return chart


def analyze_openings(games, username):
    """Analyze opening performance."""
    opening_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0, "eco": ""})

    for game in games:
        is_white = game["white"]["username"].lower() == username.lower()
        player = game["white"] if is_white else game["black"]

        result = player["result"]
        if result == "win":
            outcome = "wins"
        elif result in ["checkmated", "timeout", "resigned", "abandoned", "lose"]:
            outcome = "losses"
        else:
            outcome = "draws"

        eco_url = game.get("eco", "")
        if eco_url:
            opening_name = eco_url.split("/")[-1].replace("-", " ")
            eco_code = game.get("pgn", "")
            if "[ECO " in eco_code:
                eco = eco_code.split('[ECO "')[1].split('"')[0] if '[ECO "' in eco_code else ""
            else:
                eco = ""
            opening_stats[opening_name][outcome] += 1
            opening_stats[opening_name]["eco"] = eco

    # Calculate win rates
    openings = []
    for name, stats in opening_stats.items():
        total = stats["wins"] + stats["losses"] + stats["draws"]
        if total >= 3:
            win_rate = stats["wins"] / total * 100
            openings.append({
                "name": name,
                "win_rate": win_rate,
                "total": total,
                "wins": stats["wins"],
                "losses": stats["losses"],
                "draws": stats["draws"],
                "eco": stats["eco"]
            })

    openings.sort(key=lambda x: x["win_rate"], reverse=True)

    best = openings[:3] if len(openings) >= 3 else openings
    worst = openings[-3:] if len(openings) >= 3 else []

    return best, worst


def get_opening_image_url(opening_name, eco_code):
    """Generate URL for opening position image."""
    # Use chess.com's opening explorer images or lichess
    safe_name = opening_name.replace(" ", "-").lower()
    return f"https://www.chess.com/openings/{safe_name}"


def get_current_streak(games, username):
    """Calculate current win/loss streak."""
    if not games:
        return "No games", 0

    sorted_games = sorted(games, key=lambda g: g.get("end_time", 0), reverse=True)

    streak_type = None
    streak_count = 0

    for game in sorted_games:
        is_white = game["white"]["username"].lower() == username.lower()
        player = game["white"] if is_white else game["black"]
        result = player["result"]

        if result == "win":
            current = "W"
        elif result in ["checkmated", "timeout", "resigned", "abandoned", "lose"]:
            current = "L"
        else:
            current = "D"

        if streak_type is None:
            streak_type = current
            streak_count = 1
        elif current == streak_type:
            streak_count += 1
        else:
            break

    if streak_type == "W":
        return f"🔥 {streak_count} Win{'s' if streak_count > 1 else ''}!", streak_count
    elif streak_type == "L":
        return f"😤 {streak_count} Loss{'es' if streak_count > 1 else ''}...", streak_count
    else:
        return f"🤝 {streak_count} Draw{'s' if streak_count > 1 else ''}", streak_count


def get_last_game(games, username):
    """Get details of most recent game."""
    if not games:
        return None

    sorted_games = sorted(games, key=lambda g: g.get("end_time", 0), reverse=True)
    return sorted_games[0]


def analyze_game_with_claude(game, username):
    """Use Claude to analyze the most recent game."""
    if not ANTHROPIC_API_KEY:
        return ["API key not configured", "Add ANTHROPIC_API_KEY to secrets", "See README for instructions"]

    is_white = game["white"]["username"].lower() == username.lower()
    player = game["white"] if is_white else game["black"]
    opponent = game["black"] if is_white else game["white"]

    pgn = game.get("pgn", "No PGN available")
    result = player["result"]
    color = "White" if is_white else "Black"

    prompt = f"""Analyze this chess game and provide exactly 3 short bullet points (max 15 words each) about the most important moments or lessons.

Player: {username} (playing {color}, rated {player['rating']})
Opponent: {opponent['username']} (rated {opponent['rating']})
Result: {result}
Time Control: {game.get('time_control', 'unknown')}

PGN:
{pgn}

Provide 3 bullet points focusing on: key mistakes, good moves, or strategic lessons. Be specific about move numbers when possible. Format as:
• Point 1
• Point 2
• Point 3"""

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text

        # Parse bullet points
        lines = [l.strip() for l in response_text.split("\n") if l.strip().startswith("•")]
        return lines[:3] if lines else ["Analysis unavailable"]
    except Exception as e:
        return [f"Analysis error: {str(e)[:50]}"]


def analyze_endgames(games, username):
    """Analyze endgame performance."""
    def count_pieces(fen):
        if not fen:
            return 32
        board_part = fen.split()[0]
        return sum(1 for c in board_part if c.isalpha() and c.lower() in 'pnbrqk')

    def get_material_balance(fen, is_white):
        if not fen:
            return 0
        board_part = fen.split()[0]
        piece_values = {'p': 1, 'n': 3, 'b': 3, 'r': 5, 'q': 9, 'k': 0}
        white_mat = sum(piece_values.get(c.lower(), 0) for c in board_part if c.isupper())
        black_mat = sum(piece_values.get(c.lower(), 0) for c in board_part if c.islower())
        return white_mat - black_mat if is_white else black_mat - white_mat

    def has_queens(fen):
        if not fen:
            return True
        return 'Q' in fen.split()[0] or 'q' in fen.split()[0]

    stats = {
        "total": 0, "winning_converted": 0, "winning_drawn": 0, "winning_lost": 0,
        "losing_saved": 0, "losing_lost": 0, "equal_won": 0, "equal_lost": 0, "equal_drawn": 0
    }

    for game in games:
        fen = game.get("fen", "")
        if not fen:
            continue

        is_white = game["white"]["username"].lower() == username.lower()
        player = game["white"] if is_white else game["black"]

        result = player["result"]
        if result == "win":
            outcome = "won"
        elif result in ["checkmated", "timeout", "resigned", "abandoned", "lose"]:
            outcome = "lost"
        else:
            outcome = "drawn"

        piece_count = count_pieces(fen)
        is_endgame = piece_count <= 10 or (not has_queens(fen) and piece_count <= 16)

        if not is_endgame:
            continue

        stats["total"] += 1
        material = get_material_balance(fen, is_white)

        if material >= 3:
            if outcome == "won":
                stats["winning_converted"] += 1
            elif outcome == "drawn":
                stats["winning_drawn"] += 1
            else:
                stats["winning_lost"] += 1
        elif material <= -3:
            if outcome in ["won", "drawn"]:
                stats["losing_saved"] += 1
            else:
                stats["losing_lost"] += 1
        else:
            if outcome == "won":
                stats["equal_won"] += 1
            elif outcome == "drawn":
                stats["equal_drawn"] += 1
            else:
                stats["equal_lost"] += 1

    return stats


def generate_readme(username, stats, games):
    """Generate the README.md dashboard."""
    # Get all data
    rating_history = get_rating_history(games, username)
    elo_chart = generate_elo_chart(rating_history)
    best_openings, worst_openings = analyze_openings(games, username)
    streak_text, streak_count = get_current_streak(games, username)
    last_game = get_last_game(games, username)
    endgame_stats = analyze_endgames(games, username)

    # Get current rating
    rapid_stats = stats.get("chess_rapid", {})
    current_rating = rapid_stats.get("last", {}).get("rating", "N/A")
    best_rating = rapid_stats.get("best", {}).get("rating", "N/A")
    record = rapid_stats.get("record", {})
    wins = record.get("win", 0)
    losses = record.get("loss", 0)
    draws = record.get("draw", 0)

    # Generate last game analysis
    if last_game:
        analysis_points = analyze_game_with_claude(last_game, username)
        is_white = last_game["white"]["username"].lower() == username.lower()
        player = last_game["white"] if is_white else last_game["black"]
        opponent = last_game["black"] if is_white else last_game["white"]
        game_result = "Won" if player["result"] == "win" else "Lost" if player["result"] in ["checkmated", "timeout", "resigned", "abandoned"] else "Drew"
        game_url = last_game.get("url", "")
    else:
        analysis_points = ["No recent games"]
        game_result = "N/A"
        game_url = ""

    # Build openings section
    def format_opening(o, emoji):
        return f"{emoji} **{o['name'][:35]}** - {o['win_rate']:.0f}% ({o['wins']}W-{o['losses']}L-{o['draws']}D)"

    best_openings_text = "\n".join([format_opening(o, "🏆") for o in best_openings]) or "Not enough data"
    worst_openings_text = "\n".join([format_opening(o, "📚") for o in worst_openings]) or "Not enough data"

    # Build endgame section
    winning_total = endgame_stats["winning_converted"] + endgame_stats["winning_drawn"] + endgame_stats["winning_lost"]
    conversion_rate = (endgame_stats["winning_converted"] / winning_total * 100) if winning_total > 0 else 0

    losing_total = endgame_stats["losing_saved"] + endgame_stats["losing_lost"]
    save_rate = (endgame_stats["losing_saved"] / losing_total * 100) if losing_total > 0 else 0

    # Generate README
    readme = f"""# ♟️ {username}'s Chess Dashboard

> Auto-updated after every game

## 📊 Current Stats

| Rating | Best | Record |
|--------|------|--------|
| **{current_rating}** | {best_rating} | {wins}W - {losses}L - {draws}D |

### Current Streak: {streak_text}

---

## 📈 Rating History

{elo_chart}

---

## 📖 Opening Performance

### Best Openings
{best_openings_text}

### Openings to Study
{worst_openings_text}

---

## 🎮 Most Recent Game

**Result:** {game_result} vs {opponent['username'] if last_game else 'N/A'} ({opponent['rating'] if last_game else 'N/A'})

[View Game]({game_url})

### Analysis:
{chr(10).join(analysis_points)}

---

## ♔ Endgame Stats

| Situation | Games | Success Rate |
|-----------|-------|--------------|
| Winning (up material) | {winning_total} | {conversion_rate:.0f}% converted |
| Losing (down material) | {losing_total} | {save_rate:.0f}% saved |
| Equal endgames | {endgame_stats['equal_won'] + endgame_stats['equal_drawn'] + endgame_stats['equal_lost']} | {(endgame_stats['equal_won'] / (endgame_stats['equal_won'] + endgame_stats['equal_drawn'] + endgame_stats['equal_lost']) * 100) if (endgame_stats['equal_won'] + endgame_stats['equal_drawn'] + endgame_stats['equal_lost']) > 0 else 0:.0f}% won |

---

*Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}*

*Powered by [Chess.com API](https://www.chess.com/news/view/published-data-api) and Claude AI*
"""

    return readme


def main():
    print(f"Fetching data for {USERNAME}...")
    stats = fetch_player_stats(USERNAME)
    games = fetch_games(USERNAME)
    print(f"Found {len(games)} games")

    print("Generating dashboard...")
    readme = generate_readme(USERNAME, stats, games)

    with open("README.md", "w") as f:
        f.write(readme)

    print("Dashboard saved to README.md")


if __name__ == "__main__":
    main()
