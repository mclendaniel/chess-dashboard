#!/usr/bin/env python3
"""
Chess Dashboard Generator
Fetches chess.com data and generates a GitHub Pages website.
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

    for key, fen in OPENING_FENS.items():
        if key in name_lower or name_lower in key:
            return fen

    words = name_lower.split()
    for key, fen in OPENING_FENS.items():
        key_words = key.split()
        if any(w in key_words for w in words if len(w) > 3):
            return fen

    return "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"


def get_board_image_url(fen):
    """Generate a Lichess board image URL from FEN."""
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
        return "<p>API key not configured. Add ANTHROPIC_API_KEY to secrets.</p>"

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

Please provide analysis in this exact HTML format (no markdown, just HTML):

<div class="analysis-section">
<h4>Opening Assessment</h4>
<p>[2-3 sentences about the opening, any inaccuracies]</p>
</div>

<div class="analysis-section">
<h4>Critical Moment</h4>
<p>[Identify THE key turning point with specific moves like "After 15. Nxe5..." - 2-3 sentences]</p>
</div>

<div class="analysis-section">
<h4>Tactical Opportunities</h4>
<p>[Any missed tactics or nice combinations - 2-3 sentences]</p>
</div>

<div class="analysis-section">
<h4>Endgame Notes</h4>
<p>[If applicable, how was the endgame handled - 2-3 sentences]</p>
</div>

<div class="analysis-section highlight">
<h4>Key Lesson</h4>
<p>[One main takeaway for improvement - make this memorable and actionable]</p>
</div>

Be specific about move numbers. Use chess notation when referencing moves."""

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return f"<p class='error'>Analysis error: {str(e)[:100]}</p>"


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


def generate_html(username, stats, games):
    """Generate the index.html dashboard."""
    # Get all data
    rating_history = get_rating_history(games, username)
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

    # Rating chart data
    recent_ratings = rating_history[-30:] if rating_history else []
    ratings_json = json.dumps([r["rating"] for r in recent_ratings])
    dates_json = json.dumps([r["date"] for r in recent_ratings])

    # Last game info
    if last_game:
        analysis = analyze_game_with_claude(last_game, username)
        is_white = last_game["white"]["username"].lower() == username.lower()
        player = last_game["white"] if is_white else last_game["black"]
        opponent = last_game["black"] if is_white else last_game["white"]
        player_color = "White" if is_white else "Black"
        color_icon = "&#9817;" if is_white else "&#9823;"
        game_result = "Won" if player["result"] == "win" else "Lost" if player["result"] in ["checkmated", "timeout", "resigned", "abandoned"] else "Drew"
        result_class = "win" if game_result == "Won" else "loss" if game_result == "Lost" else "draw"
        game_url = last_game.get("url", "")
        time_control = last_game.get("time_control", "")

        if time_control:
            try:
                base = int(time_control.split("+")[0])
                tc_label = "Bullet" if base < 180 else "Blitz" if base < 600 else "Rapid"
            except:
                tc_label = "Rapid"
        else:
            tc_label = ""
    else:
        analysis = "<p>No recent games to analyze.</p>"
        game_result = "N/A"
        result_class = ""
        game_url = ""
        player_color = ""
        color_icon = ""
        tc_label = ""
        opponent = {"username": "N/A", "rating": "N/A"}

    # Streak styling
    streak_class = "win" if streak_type == "win" else "loss" if streak_type == "loss" else "draw"
    streak_icon = "&#128293;" if streak_type == "win" else "&#10052;" if streak_type == "loss" else "&#10134;"

    # Opening cards
    def opening_card(o, is_best=True):
        fen = get_opening_fen(o['name'])
        img_url = get_board_image_url(fen)
        card_class = "best" if is_best else "worst"
        return f'''
        <div class="opening-card {card_class}">
            <img src="{img_url}" alt="{o['name'][:30]}">
            <h4>{o['name'][:28]}</h4>
            <div class="win-rate">
                <div class="progress-bar">
                    <div class="progress" style="width: {o['win_rate']}%"></div>
                </div>
                <span>{o['win_rate']:.0f}%</span>
            </div>
            <div class="record">{o['wins']}W - {o['losses']}L - {o['draws']}D</div>
        </div>
        '''

    best_openings_html = "".join([opening_card(o, True) for o in best_openings]) or "<p>Not enough data yet</p>"
    worst_openings_html = "".join([opening_card(o, False) for o in worst_openings]) or "<p>Not enough data yet</p>"

    # Endgame stats
    winning_total = endgame_stats["winning_converted"] + endgame_stats["winning_drawn"] + endgame_stats["winning_lost"]
    conversion_rate = (endgame_stats["winning_converted"] / winning_total * 100) if winning_total > 0 else 0

    losing_total = endgame_stats["losing_saved"] + endgame_stats["losing_lost"]
    save_rate = (endgame_stats["losing_saved"] / losing_total * 100) if losing_total > 0 else 0

    equal_total = endgame_stats['equal_won'] + endgame_stats['equal_drawn'] + endgame_stats['equal_lost']
    equal_win_rate = (endgame_stats['equal_won'] / equal_total * 100) if equal_total > 0 else 0

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{username}'s Chess Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 2rem;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        header {{
            text-align: center;
            margin-bottom: 3rem;
        }}

        h1 {{
            font-size: 2.5rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
        }}

        .subtitle {{
            color: #888;
            font-size: 0.9rem;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .stat-card {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .stat-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.2);
        }}

        .stat-card .icon {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}

        .stat-card .value {{
            font-size: 2rem;
            font-weight: 700;
            color: #fff;
        }}

        .stat-card .label {{
            color: #888;
            font-size: 0.85rem;
            margin-top: 0.25rem;
        }}

        .stat-card.win .value {{ color: #4ade80; }}
        .stat-card.loss .value {{ color: #f87171; }}
        .stat-card.draw .value {{ color: #fbbf24; }}

        .streak-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1.5rem;
            border-radius: 50px;
            font-weight: 600;
            font-size: 1.1rem;
            margin: 1rem 0 2rem;
        }}

        .streak-badge.win {{
            background: linear-gradient(135deg, rgba(74, 222, 128, 0.2), rgba(34, 197, 94, 0.1));
            border: 1px solid rgba(74, 222, 128, 0.3);
            color: #4ade80;
        }}

        .streak-badge.loss {{
            background: linear-gradient(135deg, rgba(248, 113, 113, 0.2), rgba(239, 68, 68, 0.1));
            border: 1px solid rgba(248, 113, 113, 0.3);
            color: #f87171;
        }}

        .streak-badge.draw {{
            background: linear-gradient(135deg, rgba(251, 191, 36, 0.2), rgba(245, 158, 11, 0.1));
            border: 1px solid rgba(251, 191, 36, 0.3);
            color: #fbbf24;
        }}

        section {{
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 2rem;
            margin-bottom: 2rem;
        }}

        h2 {{
            font-size: 1.5rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        h2 .emoji {{
            font-size: 1.75rem;
        }}

        .chart-container {{
            height: 250px;
            position: relative;
        }}

        .openings-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
        }}

        .opening-card {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 1rem;
            text-align: center;
            transition: transform 0.2s;
        }}

        .opening-card:hover {{
            transform: scale(1.02);
        }}

        .opening-card.best {{
            border: 1px solid rgba(74, 222, 128, 0.3);
        }}

        .opening-card.worst {{
            border: 1px solid rgba(248, 113, 113, 0.3);
        }}

        .opening-card img {{
            width: 120px;
            height: 120px;
            border-radius: 8px;
            margin-bottom: 0.75rem;
        }}

        .opening-card h4 {{
            font-size: 0.9rem;
            color: #fff;
            margin-bottom: 0.5rem;
            height: 2.5em;
            overflow: hidden;
        }}

        .win-rate {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
        }}

        .progress-bar {{
            flex: 1;
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
        }}

        .progress {{
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 4px;
        }}

        .opening-card.best .progress {{
            background: linear-gradient(90deg, #4ade80, #22c55e);
        }}

        .opening-card.worst .progress {{
            background: linear-gradient(90deg, #f87171, #ef4444);
        }}

        .record {{
            font-size: 0.8rem;
            color: #888;
        }}

        .game-header {{
            display: flex;
            align-items: center;
            gap: 2rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
        }}

        .result-badge {{
            font-size: 1.5rem;
            font-weight: 700;
            padding: 0.5rem 1.5rem;
            border-radius: 12px;
        }}

        .result-badge.win {{
            background: rgba(74, 222, 128, 0.2);
            color: #4ade80;
        }}

        .result-badge.loss {{
            background: rgba(248, 113, 113, 0.2);
            color: #f87171;
        }}

        .result-badge.draw {{
            background: rgba(251, 191, 36, 0.2);
            color: #fbbf24;
        }}

        .game-meta {{
            display: flex;
            gap: 2rem;
            color: #888;
        }}

        .game-meta span {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .game-meta .color-icon {{
            font-size: 1.5rem;
        }}

        .view-game-btn {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            text-decoration: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            font-weight: 500;
            margin-left: auto;
            transition: opacity 0.2s;
        }}

        .view-game-btn:hover {{
            opacity: 0.9;
        }}

        .analysis-section {{
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1rem;
        }}

        .analysis-section h4 {{
            color: #667eea;
            margin-bottom: 0.5rem;
            font-size: 1rem;
        }}

        .analysis-section p {{
            line-height: 1.6;
            color: #ccc;
        }}

        .analysis-section.highlight {{
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
            border: 1px solid rgba(102, 126, 234, 0.3);
        }}

        .analysis-section.highlight h4 {{
            color: #a78bfa;
        }}

        .endgame-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
        }}

        .endgame-card {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
        }}

        .endgame-card h4 {{
            font-size: 1rem;
            margin-bottom: 1rem;
            color: #fff;
        }}

        .endgame-card .big-number {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}

        .endgame-card.winning .big-number {{ color: #4ade80; }}
        .endgame-card.losing .big-number {{ color: #f87171; }}
        .endgame-card.equal .big-number {{ color: #fbbf24; }}

        .endgame-card .detail {{
            color: #888;
            font-size: 0.85rem;
        }}

        footer {{
            text-align: center;
            color: #666;
            font-size: 0.85rem;
            margin-top: 2rem;
        }}

        footer a {{
            color: #667eea;
            text-decoration: none;
        }}

        .refresh-btn {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 50px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            margin-top: 1rem;
            transition: transform 0.2s, box-shadow 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .refresh-btn:hover {{
            transform: scale(1.05);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }}

        .refresh-btn:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }}

        .refresh-btn.loading .refresh-icon {{
            animation: spin 1s linear infinite;
        }}

        @keyframes spin {{
            from {{ transform: rotate(0deg); }}
            to {{ transform: rotate(360deg); }}
        }}

        .refresh-icon {{
            font-size: 1.2rem;
            display: inline-block;
        }}

        .toast {{
            position: fixed;
            bottom: 2rem;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0, 0, 0, 0.9);
            color: #fff;
            padding: 1rem 2rem;
            border-radius: 12px;
            font-size: 0.95rem;
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.3s;
        }}

        .toast.show {{
            opacity: 1;
        }}

        .toast.success {{
            border: 1px solid rgba(74, 222, 128, 0.5);
        }}

        .toast.error {{
            border: 1px solid rgba(248, 113, 113, 0.5);
        }}

        @media (max-width: 768px) {{
            body {{
                padding: 1rem;
            }}

            h1 {{
                font-size: 1.75rem;
            }}

            .stats-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}

            .game-header {{
                flex-direction: column;
                align-items: flex-start;
                gap: 1rem;
            }}

            .view-game-btn {{
                margin-left: 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>&#9823; {username}'s Chess Dashboard</h1>
            <p class="subtitle">Auto-updated every hour &bull; Last update: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}</p>
            <button id="refreshBtn" class="refresh-btn" onclick="refreshDashboard()">
                <span class="refresh-icon">&#8635;</span> Update Now
            </button>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="icon">&#127919;</div>
                <div class="value">{current_rating}</div>
                <div class="label">Current Rating</div>
            </div>
            <div class="stat-card">
                <div class="icon">&#11088;</div>
                <div class="value">{best_rating}</div>
                <div class="label">Peak Rating</div>
            </div>
            <div class="stat-card win">
                <div class="icon">&#9989;</div>
                <div class="value">{wins}</div>
                <div class="label">Wins</div>
            </div>
            <div class="stat-card loss">
                <div class="icon">&#10060;</div>
                <div class="value">{losses}</div>
                <div class="label">Losses</div>
            </div>
            <div class="stat-card">
                <div class="icon">&#10134;</div>
                <div class="value">{draws}</div>
                <div class="label">Draws</div>
            </div>
            <div class="stat-card">
                <div class="icon">&#128200;</div>
                <div class="value">{win_rate:.0f}%</div>
                <div class="label">Win Rate</div>
            </div>
        </div>

        <div style="text-align: center;">
            <div class="streak-badge {streak_class}">
                <span>{streak_icon}</span>
                <span>Current Streak: {streak_text}</span>
            </div>
        </div>

        <section>
            <h2><span class="emoji">&#128200;</span> Rating Trend</h2>
            <div class="chart-container">
                <canvas id="ratingChart"></canvas>
            </div>
        </section>

        <section>
            <h2><span class="emoji">&#127942;</span> Best Openings</h2>
            <div class="openings-container">
                {best_openings_html}
            </div>
        </section>

        <section>
            <h2><span class="emoji">&#128218;</span> Openings to Study</h2>
            <div class="openings-container">
                {worst_openings_html}
            </div>
        </section>

        <section>
            <h2><span class="emoji">&#127918;</span> Most Recent Game</h2>
            <div class="game-header">
                <div class="result-badge {result_class}">{game_result}</div>
                <div class="game-meta">
                    <span><span class="color-icon">{color_icon}</span> Played as {player_color}</span>
                    <span>vs {opponent['username']} ({opponent['rating']})</span>
                    <span>{tc_label}</span>
                </div>
                <a href="{game_url}" class="view-game-btn" target="_blank">View Game &#8594;</a>
            </div>

            <h3 style="margin-bottom: 1rem; color: #888; font-size: 1rem;">&#128269; Game Analysis</h3>
            {analysis}
        </section>

        <section>
            <h2><span class="emoji">&#9812;</span> Endgame Performance</h2>
            <div class="endgame-grid">
                <div class="endgame-card winning">
                    <h4>&#11014;&#65039; Winning Positions</h4>
                    <div class="big-number">{conversion_rate:.0f}%</div>
                    <div class="detail">{endgame_stats["winning_converted"]} converted / {winning_total} games</div>
                    <div class="detail">Drew {endgame_stats["winning_drawn"]} &bull; Lost {endgame_stats["winning_lost"]}</div>
                </div>
                <div class="endgame-card losing">
                    <h4>&#11015;&#65039; Losing Positions</h4>
                    <div class="big-number">{save_rate:.0f}%</div>
                    <div class="detail">{endgame_stats["losing_saved"]} saved / {losing_total} games</div>
                    <div class="detail">Wins + Draws from behind</div>
                </div>
                <div class="endgame-card equal">
                    <h4>&#9878;&#65039; Equal Positions</h4>
                    <div class="big-number">{equal_win_rate:.0f}%</div>
                    <div class="detail">{endgame_stats["equal_won"]} won / {equal_total} games</div>
                    <div class="detail">Drew {endgame_stats["equal_drawn"]} &bull; Lost {endgame_stats["equal_lost"]}</div>
                </div>
            </div>
        </section>

        <footer>
            <p>Powered by <a href="https://www.chess.com/member/{username}" target="_blank">Chess.com</a> API &amp; Claude AI</p>
        </footer>
    </div>

    <script>
        const ctx = document.getElementById('ratingChart').getContext('2d');
        const ratings = {ratings_json};
        const dates = {dates_json};

        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: dates,
                datasets: [{{
                    label: 'Rating',
                    data: ratings,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: '#667eea',
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    tooltip: {{
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        padding: 12,
                        displayColors: false,
                    }}
                }},
                scales: {{
                    x: {{
                        display: false
                    }},
                    y: {{
                        grid: {{
                            color: 'rgba(255, 255, 255, 0.05)'
                        }},
                        ticks: {{
                            color: '#888'
                        }}
                    }}
                }}
            }}
        }});
    </script>
    <div id="toast" class="toast"></div>

    <script>
        const API_URL = 'https://chess-dashboard-seven.vercel.app/api/refresh';

        function showToast(message, type) {{
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast show ' + type;
            setTimeout(() => {{
                toast.className = 'toast';
            }}, 4000);
        }}

        async function refreshDashboard() {{
            const btn = document.getElementById('refreshBtn');
            btn.disabled = true;
            btn.classList.add('loading');
            btn.innerHTML = '<span class="refresh-icon">&#8635;</span> Updating...';

            try {{
                const response = await fetch(API_URL, {{
                    method: 'POST',
                }});

                const data = await response.json();

                if (response.ok) {{
                    showToast('Update triggered! Page will refresh in ~60 seconds.', 'success');
                    // Auto-reload after 60 seconds
                    setTimeout(() => {{
                        window.location.reload();
                    }}, 60000);
                }} else {{
                    showToast('Error: ' + (data.error || 'Unknown error'), 'error');
                }}
            }} catch (error) {{
                showToast('Error: ' + error.message, 'error');
            }} finally {{
                btn.disabled = false;
                btn.classList.remove('loading');
                btn.innerHTML = '<span class="refresh-icon">&#8635;</span> Update Now';
            }}
        }}
    </script>
</body>
</html>'''

    return html


def main():
    print(f"Fetching data for {USERNAME}...")
    stats = fetch_player_stats(USERNAME)
    games = fetch_games(USERNAME)
    print(f"Found {len(games)} games")

    print("Generating dashboard...")
    html = generate_html(USERNAME, stats, games)

    with open("index.html", "w") as f:
        f.write(html)

    print("Dashboard saved to index.html")


if __name__ == "__main__":
    main()
