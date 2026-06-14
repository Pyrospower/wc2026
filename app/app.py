from flask import Flask, request, send_file, abort
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os

app = Flask(__name__)

GITHUB_BASE = "https://raw.githubusercontent.com/baburu/wc2026/refs/heads/main/cards/cropped"
BG_URL = f"{GITHUB_BASE}/01.png"

def fetch_image(url):
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content)).convert("RGBA")

def get_font(size):
    # Try to load a bold font, fall back to default
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

@app.route("/card")
def card():
    # --- params ---
    try:
        avatar_num = int(request.args.get("avatar", 2))
    except ValueError:
        abort(400, "Invalid avatar number")

    if avatar_num < 2 or avatar_num > 31:
        abort(400, "Avatar must be between 2 and 31")

    username = request.args.get("user", "Player")[:20]  # cap at 20 chars
    score    = request.args.get("score", "0")

    # --- fetch images ---
    try:
        bg     = fetch_image(BG_URL)
        avatar = fetch_image(f"{GITHUB_BASE}/{avatar_num:02d}.png")
    except Exception as e:
        abort(502, f"Could not fetch images: {e}")

    # --- composite ---
    card_img = Image.new("RGBA", (400, 600), (0, 0, 0, 0))
    card_img.paste(bg,     (0, 0))
    card_img.paste(avatar, (0, 0), avatar)  # use avatar's alpha channel

    # --- draw text into bottom bar ---
    # Bottom bar is roughly y=545–600 on the 400x600 card
    draw = ImageDraw.Draw(card_img)

    font_name  = get_font(18)
    font_score = get_font(18)

    bar_y_center = 572  # vertical center of the bottom bar

    # Username on the left side of the bar
    name_x = 55  # leave room for the soccer ball icon on the left
    draw.text(
        (name_x, bar_y_center),
        username,
        font=font_name,
        fill=(255, 255, 255, 255),
        anchor="lm"
    )

    # Score on the right side
    score_text = f"⚽ {score} pts"
    score_x = 375  # leave room for star icon on the right
    draw.text(
        (score_x, bar_y_center),
        score_text,
        font=font_score,
        fill=(255, 215, 0, 255),  # gold color
        anchor="rm"
    )

    # --- return as PNG ---
    out = io.BytesIO()
    card_img.convert("RGB").save(out, format="PNG", optimize=True)
    out.seek(0)
    return send_file(out, mimetype="image/png")

@app.route("/")
def index():
    return "WC2026 Card Service is running! Use /card?avatar=2&user=YourName&score=10"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
