import os
import csv
import requests
from io import StringIO
from flask import Flask, jsonify

app = Flask(__name__)

SHEET_CSV_URL = os.environ.get("SHEET_CSV_URL")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")


# Column layout for each leaderboard, as (name_col_index, score_col_index), 0-based.
# B=1, C=2 / E=4, F=5 / H=7, I=8 / K=10, L=11
LEADERBOARDS = {
    "lead": {"name_col": 1, "score_col": 2, "title": "GENERAL CLASSIFICATION"},
    "m1": {"name_col": 4, "score_col": 5, "title": "MATCHDAY 1"},
    "m2": {"name_col": 7, "score_col": 8, "title": "MATCHDAY 2"},
    "m3": {"name_col": 10, "score_col": 11, "title": "MATCHDAY 3"},
}


def fetch_leaderboard(name_col, score_col):
    response = requests.get(SHEET_CSV_URL, timeout=10)
    response.raise_for_status()

    reader = csv.reader(StringIO(response.text))
    players = []

    for row in reader:
        # Skip rows that don't have enough columns for this leaderboard
        if len(row) <= score_col:
            continue
        name = row[name_col].strip()
        score_raw = row[score_col].strip()

        # Skip header or non-numeric scores
        if not name or not score_raw.lstrip("-").isdigit():
            continue

        players.append((name, int(score_raw)))

    # Sort by score descending
    players.sort(key=lambda x: x[1], reverse=True)
    return players


def build_embed(players, subtitle):
    lines = ["▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"]

    for rank, (name, score) in enumerate(players, start=1):
        rank_str = f"{rank:02d}"
        # Bold blue rank, white name, bold yellow score
        line = f"\u001b[1;34m{rank_str}.\u001b[0m \u001b[0m{name:<15} \u001b[1;33m{score}\u001b[0m"
        lines.append(line)

    lines.append("▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬")
    code_block = "```ansi\n" + "\n".join(lines) + "\n```"
    description = f"🏆 **{subtitle}** 🏆\n" + code_block

    return {
        "embeds": [
            {
                "title": "WORLD CUP 2026",
                "color": 16763904,
                "description": description,
            }
        ]
    }


def post_to_discord(players, subtitle):
    payload = build_embed(players, subtitle)
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    response.raise_for_status()
    return response.status_code


def post_route_for(board_key):
    board = LEADERBOARDS[board_key]

    def handler():
        try:
            players = fetch_leaderboard(board["name_col"], board["score_col"])
            status = post_to_discord(players, board["title"])
            return jsonify({"ok": True, "players": len(players), "discord_status": status})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    return handler


def preview_route_for(board_key):
    board = LEADERBOARDS[board_key]

    def handler():
        try:
            players = fetch_leaderboard(board["name_col"], board["score_col"])
            return jsonify({"ok": True, "players": [{"name": n, "score": s} for n, s in players]})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    return handler


# /post stays as the route for -lead (General Classification), unchanged from before.
# /m1, /m2, /m3 are the new commands' routes.
app.add_url_rule("/post", "post_lead", post_route_for("lead"), methods=["GET", "POST"])
app.add_url_rule("/preview", "preview_lead", preview_route_for("lead"), methods=["GET"])

for key in ("m1", "m2", "m3"):
    app.add_url_rule(f"/{key}", f"post_{key}", post_route_for(key), methods=["GET", "POST"])
    app.add_url_rule(f"/{key}/preview", f"preview_{key}", preview_route_for(key), methods=["GET"])


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "running"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
