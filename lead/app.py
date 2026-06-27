import os
import csv
import requests
from datetime import datetime, timezone
from io import StringIO
from flask import Flask, jsonify, send_from_directory, request

app = Flask(__name__)

SHEET_CSV_URL = os.environ.get("SHEET_CSV_URL")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")


# Column and row layouts for each leaderboard (0-based indexes)
# Spreadsheet Rows 2-15 -> index 1:15 | Rows 18-31 -> index 17:31
LEADERBOARDS = {
    "lead": {"name_col": 1, "score_col": 2, "title": "GENERAL CLASSIFICATION", "start_row": 1, "end_row": 15},
    "m1": {"name_col": 4, "score_col": 5, "title": "MATCHDAY 1", "start_row": 1, "end_row": 15},
    "m2": {"name_col": 7, "score_col": 8, "title": "MATCHDAY 2", "start_row": 1, "end_row": 15},
    "m3": {"name_col": 10, "score_col": 11, "title": "MATCHDAY 3", "start_row": 1, "end_row": 15},
    "m4": {"name_col": 1, "score_col": 2, "title": "MATCHDAY 4", "start_row": 17, "end_row": 31},
}


def fetch_leaderboard(name_col, score_col, start_row, end_row):
    response = requests.get(SHEET_CSV_URL, timeout=10)
    response.raise_for_status()

    # Convert to a list to easily slice by row indices
    reader = list(csv.reader(StringIO(response.text)))
    players = []

    for row in reader[start_row:end_row]:
        required_len = max(name_col, score_col) + 1
        if len(row) < required_len:
            row += [""] * (required_len - len(row))

        name = row[name_col].strip()
        score_raw = row[score_col].strip()

        if not name or not score_raw.lstrip("-").isdigit():
            continue

        players.append((name, int(score_raw)))

    players.sort(key=lambda x: x[1], reverse=True)
    return players


def build_embed(players, subtitle):
    lines = ["▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"]

    for rank, (name, score) in enumerate(players, start=1):
        rank_str = f"{rank:02d}"
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
    now = datetime.now(timezone.utc).isoformat()
    requester_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    user_agent = request.headers.get("User-Agent", "unknown")
    print(f"[WEBHOOK-POST] {now} | path={request.path} | ip={requester_ip} | ua={user_agent}", flush=True)
    payload = build_embed(players, subtitle)
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    if response.status_code == 429:
        print(f"[WEBHOOK-429] {now} | retry_after={response.headers.get('Retry-After')} | body={response.text}", flush=True)
    response.raise_for_status()
    return response.status_code


def post_route_for(board_key):
    board = LEADERBOARDS[board_key]

    def handler():
        try:
            players = fetch_leaderboard(board["name_col"], board["score_col"], board["start_row"], board["end_row"])
            status = post_to_discord(players, board["title"])
            return jsonify({"ok": True, "players": len(players), "discord_status": status})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    handler.__name__ = f"post_handler_{board_key}"
    return handler


def preview_route_for(board_key):
    board = LEADERBOARDS[board_key]

    def handler():
        try:
            players = fetch_leaderboard(board["name_col"], board["score_col"], board["start_row"], board["end_row"])
            return jsonify({"ok": True, "players": [{"name": n, "score": s} for n, s in players]})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    handler.__name__ = f"preview_handler_{board_key}"
    return handler


app.add_url_rule("/post", "post_lead", post_route_for("lead"), methods=["GET", "POST"])
app.add_url_rule("/preview", "preview_lead", preview_route_for("lead"), methods=["GET"])

# Added "m4" to the endpoints loop
for key in ("m1", "m2", "m3", "m4"):
    app.add_url_rule(f"/{key}", f"post_{key}", post_route_for(key), methods=["GET", "POST"])
    app.add_url_rule(f"/{key}/preview", f"preview_{key}", preview_route_for(key), methods=["GET"])


@app.route("/ui")
def ui():
    return send_from_directory("static", "index.html")


@app.route("/ui/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "running"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)