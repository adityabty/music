import os
import random
import aiohttp
import aiofiles
import traceback
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from youtubesearchpython.__future__ import VideosSearch
from XMUSIC.core.dir import CACHE_DIR
from config import YOUTUBE_IMG_URL


# ---------------- CONSTANTS ----------------
CANVAS_W, CANVAS_H = 1280, 720

FONT_REGULAR_PATH = "XMUSIC/assets/thumb/font.ttf"
FONT_BOLD_PATH = "XMUSIC/assets/thumb/font2.ttf"
DEFAULT_THUMB = "XMUSIC/assets/thumb/default.png"

CACHE_DIR = Path(CACHE_DIR)
CACHE_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------
# BASIC UTILITIES
# ---------------------------------------------------
def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""

    for w in words:
        test = current + (" " if current else "") + w
        if draw.textlength(test, font=font) <= max_width:
            current = test
        else:
            lines.append(current)
            current = w

    if current:
        lines.append(current)

    return lines[:2]


def create_shape_mask(size, shape="circle"):
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)

    if shape == "circle":
        draw.ellipse((0, 0, size, size), fill=255)

    elif shape == "rounded":
        draw.rounded_rectangle((0, 0, size, size), radius=40, fill=255)

    else:
        draw.rectangle((0, 0, size, size), fill=255)

    return mask


def random_gradient():
    colors = [
        ((40, 0, 70), (120, 0, 160)), 
        ((0, 40, 60), (0, 120, 180)),
        ((60, 10, 0), (200, 60, 0)),
        ((20, 20, 20), (80, 80, 80)),
        ((10, 0, 30), (80, 0, 150)),
    ]
    return random.choice(colors)


def apply_gradient(img, colors):
    c1, c2 = colors
    w, h = img.size
    base = Image.new("RGBA", (w, h), c1)
    top = Image.new("RGBA", (w, h), c2)

    mask = Image.new("L", (w, h))
    md = ImageDraw.Draw(mask)

    for y in range(h):
        md.line([(0, y), (w, y)], fill=int(255 * (y / h)))

    return Image.composite(top, base, mask)


def random_layout():
    return {
        "art_size": random.randint(350, 420),
        "art_x": random.randint(80, 180),
        "art_shape": random.choice(["circle", "rounded"]),
        "text_align": random.choice(["left", "right"]),
        "show_particles": random.choice([True, False])
    }


def random_accent_color():
    return random.choice([
        (255, 90, 90),
        (255, 160, 60),
        (100, 230, 255),
        (255, 60, 220),
        (160, 255, 80),
    ])


def add_particles(draw, color):
    for _ in range(80):
        x = random.randint(0, CANVAS_W)
        y = random.randint(0, CANVAS_H)
        r = random.randint(2, 5)
        draw.ellipse((x, y, x + r, y + r), fill=(*color, 120))


def add_glow_ring(canvas, x, y, size, color, thickness):
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    draw.ellipse(
        (thickness, thickness, size - thickness, size - thickness),
        outline=(*color, 180),
        width=thickness
    )
    glow = glow.filter(ImageFilter.GaussianBlur(20))
    canvas.alpha_composite(glow, (x, y))


# ---------------------------------------------------
# MAIN FUNCTION (XMUSIC USES THIS)
# ---------------------------------------------------
async def get_thumb(videoid: str):
    """
    XMUSIC Thumbnail Generator (Updated)
    """

    url = f"https://www.youtube.com/watch?v={videoid}"
    thumb_path = None

    # ---------------- GET VIDEO DATA ----------------
    try:
        search = VideosSearch(url, limit=1)
        data = (await search.next())["result"][0]

        title = data.get("title", "Unknown Title")
        duration = data.get("duration", "0:00")
        views = data.get("viewCount", {}).get("short", "0 Views")
        channel = data.get("channel", {}).get("name", "Unknown Channel")

        # fetch thumbnail
        t_url = data["thumbnails"][0]["url"].split("?")[0]

        async with aiohttp.ClientSession() as session:
            async with session.get(t_url) as r:
                if r.status == 200:
                    thumb_path = CACHE_DIR / f"{videoid}.png"
                    async with aiofiles.open(thumb_path, "wb") as f:
                        await f.write(await r.read())

        base_img = Image.open(thumb_path).convert("RGBA")

    except Exception:
        print("Thumbnail fetch error — using default.")
        base_img = Image.open(DEFAULT_THUMB).convert("RGBA")

    # ---------------- CREATE FINAL CANVAS ----------------
    try:
        canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0))
        canvas = apply_gradient(canvas, random_gradient())

        layout = random_layout()
        accent = random_accent_color()

        if layout["show_particles"]:
            add_particles(ImageDraw.Draw(canvas), accent)

        art = base_img.resize((layout["art_size"], layout["art_size"]))
        mask = create_shape_mask(layout["art_size"], layout["art_shape"])
        art.putalpha(mask)

        art_y = (CANVAS_H - layout["art_size"]) // 2
        canvas.paste(art, (layout["art_x"], art_y), art)

        draw = ImageDraw.Draw(canvas)

        # Title
        title_font = ImageFont.truetype(FONT_BOLD_PATH, 44)
        max_w = 650
        txt_x = 720 if layout["text_align"] == "right" else 60
        txt_y = 180

        lines = wrap_text(draw, title, title_font, max_w)
        draw.multiline_text((txt_x, txt_y), "\n".join(lines), font=title_font, fill=(255, 255, 255))

        # Meta info
        meta_font = ImageFont.truetype(FONT_REGULAR_PATH, 32)
        draw.text((txt_x, txt_y + 150), f"{views}", fill=(240, 240, 240), font=meta_font)
        draw.text((txt_x, txt_y + 200), f"{duration}", fill=(230, 230, 230), font=meta_font)
        draw.text((txt_x, txt_y + 250), f"{channel}", fill=(230, 230, 230), font=meta_font)

        out = CACHE_DIR / f"{videoid}_final.png"
        canvas.save(out, optimize=True)

        return str(out)

    except Exception as e:
        traceback.print_exc()
        print("Thumbnail generation failed:", e)
        return None
