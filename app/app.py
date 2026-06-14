from flask import Flask, request, send_file, abort
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os

app = Flask(__name__)

GITHUB_BASE = "https://raw.githubusercontent.com/baburu/wc2026/refs/heads/main/cards/cropped"
BG_URL = f"{GITHUB_BASE}/01.png"

FONT_PATH = "/tmp/font_bold.ttf"
FONT_URL  = "https://github.com/google/fonts/raw/main/apache/roboto/Roboto%5Bwdth%2Cwght%5D.ttf"

def ensure_font():
    if not os.path.exists(FONT_PATH):
        r = requests.get(FONT_URL, timeout=15)
        r.raise_for_status()
        with open(FONT_PATH, "wb") as f:
            f.write(r.content)

def fetch_image(url):
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content)).convert("RGBA")

def get_font(size):
    ensure_font()
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        for path in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        return ImageFont.load_default()

@app.route("/card")
def card():
    try:
        avatar_num = int(request.args.get("avatar", 2))
    except ValueError:
        abort(400, "Invalid avatar number")

    if avatar_num < 2 or avatar_num > 31:
        abort(400, "Avatar must be between 2 and 31")

    username = request.args.get("user", "Player")[:20].upper()
    score    = request.args.get("score", "0")

    try:
        bg     = fetch_image(BG_URL)
        avatar = fetch_image(f"{GITHUB_BASE}/{avatar_num:02d}.png")
    except Exception as e:
        abort(502, f"Could not fetch images: {e}")

    card_img = Image.new("RGBA", (400, 600), (0, 0, 0, 0))
    card_img.paste(bg,     (0, 0))
    card_img.paste(avatar, (0, 0), avatar)

    draw = ImageDraw.Draw(card_img)

    font_name  = get_font(28)  # large bold for username
    font_score = get_font(16)  # smaller for score

    cx = 200  # horizontal center

    # Username — large, white, centered at ~y=520 (inside dark bar, top line)
    draw.text(
        (cx, 518),
        username,
        font=font_name,
        fill=(255, 255, 255, 255),
        anchor="mm"
    )

    # Score — smaller, white, centered below
    draw.text(
        (cx, 548),
        f"SCORE: {score} PTS",
        font=font_score,
        fill=(255, 255, 255, 255),
        anchor="mm"
    )

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
