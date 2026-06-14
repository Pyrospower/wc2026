from flask import Flask, request, send_file, abort
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os

app = Flask(__name__)

GITHUB_BASE = "https://raw.githubusercontent.com/baburu/wc2026/refs/heads/main/cards/cropped"
BG_URL = f"{GITHUB_BASE}/01.png"

# In-memory image cache
_image_cache = {}

def fetch_image(url):
    if url in _image_cache:
        return _image_cache[url].copy()
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
    _image_cache[url] = img
    return img.copy()

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

    font_name  = get_font(32)
    font_score = get_font(16)

    cx = 200

    draw.text((cx, 518), username,              font=font_name,  fill=(242, 235, 213, 255), anchor="mm")
    draw.text((cx, 550), f"SCORE: {score} PTS", font=font_score, fill=(100, 20, 40, 255),   anchor="mm")

    out = io.BytesIO()
    card_img.convert("RGB").save(out, format="PNG", optimize=True)
    out.seek(0)
    return send_file(out, mimetype="image/png")

@app.route("/warmup")
def warmup():
    """Pre-cache all avatars — call this once after deploy"""
    errors = []
    try:
        fetch_image(BG_URL)
    except Exception as e:
        errors.append(f"bg: {e}")
    for i in range(2, 32):
        try:
            fetch_image(f"{GITHUB_BASE}/{i:02d}.png")
        except Exception as e:
            errors.append(f"avatar {i}: {e}")
    if errors:
        return f"Done with errors: {errors}"
    return "✅ All 31 images cached!"

@app.route("/")
def index():
    return "WC2026 Card Service is running! Use /card?avatar=2&user=YourName&score=10"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
