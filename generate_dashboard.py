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
import urllib.parse

USERNAME = "skilletobviously"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

HEADERS = {"User-Agent": "Chess Dashboard Generator"}

# Common opening FENs for board images
OPENING_FENS = {
    "kings pawn opening": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
    "queens pawn opening": "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq d3 0 1",
    "sicilian defense": "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2",
    "french defense": "rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
    "caro kann defense": "rnbqkbnr/pp1ppppp/2p5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
    "italian game": "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",
    "ruy lopez": "r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",
    "scotch game": "r1bqkbnr/pppp1ppp/2n5/4p3/3PP3/5N2/PPP2PPP/RNBQKB1R b KQkq d3 0 3",
    "vienna game": "rnbqkbnr/pppp1ppp/8/4p3/4P3/2N5/PPPP1PPP/R1BQKBNR b KQkq - 1 2",
    "four knights game": "r1bqkb1r/pppp1ppp/2n2n2/4p3/4P3/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 4 4",
    "pirc defense": "rnbqkbnr/ppp1pppp/3p4/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
    "scandinavian defense": "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2",
    "kings indian defense": "rnbqkb1r/pppppp1p/5np1/8/2PP4/8/PP2PPPP/RNBQKBNR w KQkq - 0 3",
    "queens gambit": "rnbqkbnr/ppp1pppp/8/3p4/2PP4/8/PP2PPPP/RNBQKBNR b KQkq c3 0 2",
    "london system": "rnbqkbnr/ppp1pppp/8/3p4/3P1B2/8/PPP1PPPP/RN1QKBNR b KQkq - 1 2",
    "english opening": "rnbqkbnr/pppppppp/8/8/2P5/8/PP1PPPPP/RNBQKBNR b KQkq c3 0 1",
    "philidor defense": "rnbqkbnr/ppp2ppp/3p4/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 3",
    "petrov defense": "rnbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
    "three knights opening": "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/2N2N2/PPPP1PPP/R1BQKB1R b KQkq - 3 3",
    "bishops opening": "rnbqkbnr/pppp1ppp/8/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR b KQkq - 1 2",
    "center game": "rnbqkbnr/pppp1ppp/8/4p3/3PP3/8/PPP2PPP/RNBQKBNR b KQkq d3 0 2",
    "alekhine defense": "rnbqkb1r/pppppppp/5n2/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 2",
}


def get_opening_fen(opening_name):
    """Find the best matching FEN for an opening."""
    name_lower = opening_name.lower()

    # Try exact matches first
    for key, fen in OPENING_FENS.items():
        if key in name_lower or name_lower in key:
            return fen

    # Try partial word matches
    words = name_lower.split()
    for key, fen in OPENING_FENS.items():
        key_words = key.split()
        if any(w in key_words for w in words if len(w) > 3):
            return fen

    # Default to starting position
    return "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"


def get_board_image_url(fen, size=180):
    """Generate a Lichess board image URL from FEN."""
    # Use Lichess board image API
    encoded_fen = urllib.parse.quote(fen, safe='')
    return f"https://lichess1.org/export/fen.gif?fen={encoded_fen}&color=white&theme=brown&piece=cburnett"


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
    trend = "📈" if change >= 0 else "📉"

    return current, min_r, max_r, change, sparkline, trend, len(recent)


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


def get_current_streak(games, username):
    """Calculate current win/loss streak."""
    if not games:
        return "No games", 0, "neutral"

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
        return f"{streak_count} Win{'s' if streak_count > 1 else ''}", streak_count, "win"
    elif streak_type == "L":
        return f"{streak_count} Loss{'es' if streak_count > 1 else ''}", streak_count, "loss"
    else:
        return f"{streak_count} Draw{'s' if streak_count > 1 else ''}", streak_count, "draw"


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

    prompt = f"""You are a chess coach analyzing a game for a student. Provide a detailed but accessible analysis.

Player: {username} (playing as {color}, rated {player['rating']})
Opponent: {opponent['username']} (rated {opponent['rating']})
Result: {result}
Time Control: {game.get('time_control', 'unknown')}

PGN:
{pgn}

Please provide:
1. **Opening Assessment**: How did the opening go? Any inaccuracies?
2. **Critical Moment**: Identify THE key turning point with specific moves (e.g., "After 15. Nxe5, the position changed because...")
3. **Tactical Opportunities**: Any missed tactics or nice combinations?
4. **Endgame Notes**: If applicable, how was the endgame handled?
5. **Key Lesson**: One main takeaway for improvement

Format your response in markdown with headers. Be specific about move numbers. Keep each section to 2-3 sentences max. Use chess notation when referencing moves."""

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return f"Analysis error: {str(e)[:100]}"


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


def generate_progress_bar(percentage, length=10):
    """Generate a text progress bar."""
    filled = int(percentage / 100 * length)
    empty = length - filled
    return "█" * filled + "░" * empty


def generate_readme(username, stats, games):
    """Generate the README.md dashboard."""
    # Get all data
    rating_history = get_rating_history(games, username)
    chart_data = generate_elo_chart(rating_history)
    best_openings, worst_openings = analyze_openings(games, username)
    streak_text, streak_count, streak_type = get_current_streak(games, username)
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
    total_games = wins + losses + draws
    win_rate = (wins / total_games * 100) if total_games > 0 else 0

    # Chart data
    if chart_data != "No rating data available.":
        current, min_r, max_r, change, sparkline, trend, num_games = chart_data
    else:
        current, min_r, max_r, change, sparkline, trend, num_games = "N/A", 0, 0, 0, "", "📊", 0

    # Generate last game analysis
    if last_game:
        analysis = analyze_game_with_claude(last_game, username)
        is_white = last_game["white"]["username"].lower() == username.lower()
        player = last_game["white"] if is_white else last_game["black"]
        opponent = last_game["black"] if is_white else last_game["white"]
        player_color = "White ⬜" if is_white else "Black ⬛"
        game_result = "Won ✓" if player["result"] == "win" else "Lost ✗" if player["result"] in ["checkmated", "timeout", "resigned", "abandoned"] else "Drew ="
        game_url = last_game.get("url", "")
        time_control = last_game.get("time_control", "")

        # Parse time control
        if time_control:
            try:
                base = int(time_control.split("+")[0])
                if base < 180:
                    tc_label = "Bullet"
                elif base < 600:
                    tc_label = "Blitz"
                else:
                    tc_label = "Rapid"
            except:
                tc_label = "Rapid"
        else:
            tc_label = ""
    else:
        analysis = "No recent games to analyze."
        game_result = "N/A"
        game_url = ""
        player_color = ""
        tc_label = ""
        opponent = {"username": "N/A", "rating": "N/A"}

    # Streak styling
    if streak_type == "win":
        streak_emoji = "🔥"
        streak_badge_color = "brightgreen"
    elif streak_type == "loss":
        streak_emoji = "❄️"
        streak_badge_color = "red"
    else:
        streak_emoji = "➖"
        streak_badge_color = "yellow"

    # Build openings section with images
    def format_opening_card(o, is_best=True):
        fen = get_opening_fen(o['name'])
        img_url = get_board_image_url(fen)
        emoji = "🏆" if is_best else "📚"
        win_bar = generate_progress_bar(o['win_rate'])

        return f"""<td align="center" width="200">
<img src="{img_url}" width="120" alt="{o['name'][:30]}"/><br/>
<strong>{o['name'][:25]}</strong><br/>
<code>{win_bar} {o['win_rate']:.0f}%</code><br/>
<sub>{o['wins']}W - {o['losses']}L - {o['draws']}D</sub>
</td>"""

    best_openings_html = ""
    if best_openings:
        best_openings_html = "<table><tr>\n"
        for o in best_openings:
            best_openings_html += format_opening_card(o, True) + "\n"
        best_openings_html += "</tr></table>"
    else:
        best_openings_html = "<em>Not enough data yet</em>"

    worst_openings_html = ""
    if worst_openings:
        worst_openings_html = "<table><tr>\n"
        for o in worst_openings:
            worst_openings_html += format_opening_card(o, False) + "\n"
        worst_openings_html += "</tr></table>"
    else:
        worst_openings_html = "<em>Not enough data yet</em>"

    # Build endgame section
    winning_total = endgame_stats["winning_converted"] + endgame_stats["winning_drawn"] + endgame_stats["winning_lost"]
    conversion_rate = (endgame_stats["winning_converted"] / winning_total * 100) if winning_total > 0 else 0

    losing_total = endgame_stats["losing_saved"] + endgame_stats["losing_lost"]
    save_rate = (endgame_stats["losing_saved"] / losing_total * 100) if losing_total > 0 else 0

    equal_total = endgame_stats['equal_won'] + endgame_stats['equal_drawn'] + endgame_stats['equal_lost']
    equal_win_rate = (endgame_stats['equal_won'] / equal_total * 100) if equal_total > 0 else 0

    # Generate README
    readme = f"""<div align="center">

# ♟️ {username}'s Chess Dashboard

<img src="https://img.shields.io/badge/Rating-{current_rating}-blue?style=for-the-badge&logo=lichess&logoColor=white" alt="Rating"/>
<img src="https://img.shields.io/badge/Best-{best_rating}-gold?style=for-the-badge" alt="Best"/>
<img src="https://img.shields.io/badge/Win_Rate-{win_rate:.0f}%25-green?style=for-the-badge" alt="Win Rate"/>
<img src="https://img.shields.io/badge/{streak_text.replace(' ', '_')}-{streak_badge_color}?style=for-the-badge" alt="Streak"/>

<sub>Auto-updated every hour • Last update: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}</sub>

</div>

---

## 📊 Stats at a Glance

<table>
<tr>
<td align="center" width="150">
<h3>🎯</h3>
<h2>{current_rating}</h2>
<sub>Current Rating</sub>
</td>
<td align="center" width="150">
<h3>⭐</h3>
<h2>{best_rating}</h2>
<sub>Peak Rating</sub>
</td>
<td align="center" width="150">
<h3>✅</h3>
<h2>{wins}</h2>
<sub>Wins</sub>
</td>
<td align="center" width="150">
<h3>❌</h3>
<h2>{losses}</h2>
<sub>Losses</sub>
</td>
<td align="center" width="150">
<h3>➖</h3>
<h2>{draws}</h2>
<sub>Draws</sub>
</td>
</tr>
</table>

### {streak_emoji} Current Streak: {streak_text}

---

## 📈 Rating Trend

```
{trend} {'+' if change >= 0 else ''}{change} over last {num_games} games

{sparkline}

     Low: {min_r}                    High: {max_r}
```

---

## 📖 Opening Performance

### 🏆 Best Openings

{best_openings_html}

### 📚 Openings to Study

{worst_openings_html}

---

## 🎮 Most Recent Game

<table>
<tr>
<td width="50%">

### {game_result}

| | |
|---|---|
| **Played as** | {player_color} |
| **Opponent** | {opponent['username']} ({opponent['rating']}) |
| **Format** | {tc_label} |

<a href="{game_url}">
<img src="https://img.shields.io/badge/View_Game-chess.com-green?style=for-the-badge&logo=chess.com" alt="View Game"/>
</a>

</td>
</tr>
</table>

### 🔍 Game Analysis

{analysis}

---

## ♔ Endgame Performance

<table>
<tr>
<td align="center" width="250">
<h3>⬆️ Winning Positions</h3>
<code>{generate_progress_bar(conversion_rate)} {conversion_rate:.0f}%</code><br/>
<strong>{endgame_stats["winning_converted"]}</strong> converted / {winning_total} games<br/>
<sub>Drew {endgame_stats["winning_drawn"]} • Lost {endgame_stats["winning_lost"]}</sub>
</td>
<td align="center" width="250">
<h3>⬇️ Losing Positions</h3>
<code>{generate_progress_bar(save_rate)} {save_rate:.0f}%</code><br/>
<strong>{endgame_stats["losing_saved"]}</strong> saved / {losing_total} games<br/>
<sub>Wins + Draws from losing</sub>
</td>
<td align="center" width="250">
<h3>⚖️ Equal Positions</h3>
<code>{generate_progress_bar(equal_win_rate)} {equal_win_rate:.0f}%</code><br/>
<strong>{endgame_stats["equal_won"]}</strong> won / {equal_total} games<br/>
<sub>Drew {endgame_stats["equal_drawn"]} • Lost {endgame_stats["equal_lost"]}</sub>
</td>
</tr>
</table>

---

<div align="center">

<sub>Powered by <a href="https://www.chess.com/member/{username}">Chess.com</a> API & Claude AI</sub>

</div>
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
