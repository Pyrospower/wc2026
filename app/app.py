from flask import Flask, request, send_file, abort
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os

app = Flask(__name__)

GITHUB_BASE = "https://raw.githubusercontent.com/baburu/wc2026/refs/heads/main/cards/cropped"
LEADERBOARD_URL = "https://wc2026-leaderboard.onrender.com/preview"

# Valid background keys → filenames in GitHub
BG_NAMES = {
    "default": "base.png",
    "gc":      "gc.png",
    "m":       "m.png",
}

# Score text color per background key, matching each card's border/theme color
SCORE_COLORS = {
    "default": (100, 20, 40, 255),
    "gc":      (20, 70, 160, 255),   # blue, matches the gc.png border
    "m":       (150, 20, 30, 255),   # red, matches the m.png border
}

# Discord username (lowercase) -> Sheet name
NAME_MAP = {
    "baburubaburu": "Babu",
    "houtarou": "Hotarou",
    "ziggssawpuzzle":"Ziggs",
    "trel":         "Trel",
    "scorpy":       "Scorpy",
    "pyrospower":   "Pyro",
    "edna_san":     "Edna",
    "bimbastic":    "BimBim",
    "squallyy":      "Squally",
    "hypetrain":    "Hype",
    "sunnyrainlight":"Sunny",
    "akuma5336": "D4",
    "nyte_zero":    "Nyte",
    "xenter0384":   "Pffq",
}

_image_cache = {}
_score_cache = {}

def fetch_image(url):
    if url in _image_cache:
        return _image_cache[url].copy()
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
    _image_cache[url] = img
    return img.copy()

def fetch_score(discord_username):
    sheet_name = NAME_MAP.get(discord_username.lower())
    if not sheet_name:
        return "0"
    try:
        resp = requests.get(LEADERBOARD_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        for player in data.get("players", []):
            if player["name"] == sheet_name:
                return str(player["score"])
    except Exception:
        pass
    return "0"

def get_font(size):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)

VALID_BADGES = {"m1", "m2", "m3"}

# --- Badge layout config: edit these to resize/reposition the badge row ---
BADGE_SIZE   = 100   # size (px) each badge is scaled into on the 400x600 card
BADGE_GAP    = 14   # gap (px) between badges
BADGE_LEFT_X = 35   # left margin (px) where the badge row starts
BADGE_Y      = 430  # vertical center (px) of the badge row

# Safety clamp so a typo'd BADGE_SIZE can't break the card layout
BADGE_SIZE = max(16, min(BADGE_SIZE, 120))
# ---------------------------------------------------------------------


@app.route("/card")
def card():
    try:
        avatar_num = int(request.args.get("avatar", 2))
    except ValueError:
        abort(400, "Invalid avatar number")

    if avatar_num < 2 or avatar_num > 31:
        abort(400, "Avatar must be between 2 and 31")

    username = request.args.get("user", "Player")[:20]
    score    = fetch_score(username)
    raw_badges = request.args.get("badge", "")
    badges = [b.strip().lower() for b in raw_badges.split(",") if b.strip()]
    badges = [b for b in badges if b in VALID_BADGES]
    username = username.upper()

    # Background: pick from BG_NAMES, fall back to default
    bg_key = request.args.get("bg", "default").strip().lower()
    bg_filename = BG_NAMES.get(bg_key, "01.png")
    bg_url = f"{GITHUB_BASE}/{bg_filename}"

    try:
        bg     = fetch_image(bg_url)
        avatar = fetch_image(f"{GITHUB_BASE}/{avatar_num:02d}.png")
    except Exception as e:
        abort(502, f"Could not fetch images: {e}")

    badge_imgs = []
    for b in badges:
        try:
            badge_imgs.append(fetch_image(f"{GITHUB_BASE}/{b}.png"))
        except Exception:
            pass  # missing/broken badge file shouldn't break the whole card

    card_img = Image.new("RGBA", (400, 600), (0, 0, 0, 0))
    card_img.paste(bg, (0, 0))
    card_img.paste(avatar, (0, 0), avatar)
    bar_region = bg.crop((0, 500, 400, 600))
    card_img.paste(bar_region, (0, 500))

    draw = ImageDraw.Draw(card_img)

    font_name  = get_font(32)
    font_score = get_font(16)

    cx = 200

    if badge_imgs:
        x = BADGE_LEFT_X
        for img in badge_imgs:
            resized = img.copy()
            resized.thumbnail((BADGE_SIZE, BADGE_SIZE))
            bw, bh = resized.size
            card_img.paste(resized, (x, BADGE_Y - bh // 2), resized)
            x += BADGE_SIZE + BADGE_GAP

    score_color = SCORE_COLORS.get(bg_key, SCORE_COLORS["default"])

    draw.text((cx, 508), username,              font=font_name,  fill=(242, 235, 213, 255), anchor="mm")
    draw.text((cx, 554), f"SCORE: {score} PTS", font=font_score, fill=score_color,          anchor="mm")

    out = io.BytesIO()
    card_img.convert("RGB").save(out, format="PNG", optimize=True)
    out.seek(0)
    return send_file(out, mimetype="image/png")

@app.route("/warmup")
def warmup():
    errors = []
    for bg_filename in BG_NAMES.values():
        try:
            fetch_image(f"{GITHUB_BASE}/{bg_filename}")
        except Exception as e:
            errors.append(f"bg {bg_filename}: {e}")
    for i in range(2, 32):
        try:
            fetch_image(f"{GITHUB_BASE}/{i:02d}.png")
        except Exception as e:
            errors.append(f"avatar {i}: {e}")
    for badge in VALID_BADGES:
        try:
            fetch_image(f"{GITHUB_BASE}/{badge}.png")
        except Exception as e:
            errors.append(f"badge {badge}: {e}")
    if errors:
        return f"Done with errors: {errors}"
    return "✅ All images cached!"

@app.route("/")
def index():
    return "WC2026 Card Service is running! Use /card?avatar=2&user=YourName&bg=gc"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)