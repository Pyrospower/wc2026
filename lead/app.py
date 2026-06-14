import os
import csv
import requests
from io import StringIO
from flask import Flask, jsonify

app = Flask(__name__)

SHEET_CSV_URL = os.environ.get("SHEET_CSV_URL")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")


def fetch_leaderboard():
    response = requests.get(SHEET_CSV_URL, timeout=10)
    response.raise_for_status()

    reader = csv.reader(StringIO(response.text))
    players = []

    for row in reader:
        # Skip empty rows or rows without both columns
        if len(row) < 3:
            continue
        name = row[1].strip()
        score_raw = row[2].strip()

        # Skip header or non-numeric scores
        if not name or not score_raw.lstrip("-").isdigit():
            continue

        players.append((name, int(score_raw)))

    # Sort by score descending
    players.sort(key=lambda x: x[1], reverse=True)
    return players


def build_embed(players):
    lines = ["▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"]

    for rank, (name, score) in enumerate(players, start=1):
        rank_str = f"{rank:02d}"
        # Bold blue rank, white name, bold yellow score
        line = f"\u001b[1;34m{rank_str}.\u001b[0m \u001b[0m{name:<15} \u001b[1;33m{score}\u001b[0m"
        lines.append(line)

    lines.append("▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬")
    code_block = "```ansi\n" + "\n".join(lines) + "\n```"
    description = "🏆 **CURRENT LEADERBOARD** 🏆\n" + code_block

    return {
        "embeds": [
            {
                "title": "WORLD CUP 2026",
                "color": 16763904,
                "description": description,
            }
        ]
    }


def post_to_discord(players):
    payload = build_embed(players)
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    response.raise_for_status()
    return response.status_code


@app.route("/post", methods=["GET", "POST"])
def post_leaderboard():
    try:
        players = fetch_leaderboard()
        status = post_to_discord(players)
        return jsonify({"ok": True, "players": len(players), "discord_status": status})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/preview", methods=["GET"])
def preview_leaderboard():
    """Returns the leaderboard data as JSON without posting to Discord — useful for debugging."""
    try:
        players = fetch_leaderboard()
        return jsonify({"ok": True, "players": [{"name": n, "score": s} for n, s in players]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "running"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
