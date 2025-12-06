import os
import random
import aiohttp
import aiofiles
import traceback
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from youtubesearchpython.__future__ import VideosSearch
from XMUSIC.core.dir import CACHE_DIR

# ---------------- CONSTANTS ----------------
CANVAS_W, CANVAS_H = 1280, 720

FONT_REGULAR_PATH = "XMUSIC/assets/thumb/font.ttf"
FONT_BOLD_PATH   = "XMUSIC/assets/thumb/font2.ttf"
DEFAULT_THUMB    = "XMUSIC/assets/thumb/IMG_20251204_211306_982.jpg"

CACHE_DIR = Path(CACHE_DIR)
CACHE_DIR.mkdir(exist_ok=True)


# ---------------- UTILITIES ----------------
def wrap_text(draw, text, font, max_width):
    try:
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
    except:
        return [text]


def create_shape_mask(size, shape="circle"):
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)

    if shape == "circle":
        draw.ellipse((0, 0, size, size), fill=255)
    else:
        draw.rounded_rectangle((0, 0, size, size), radius=40, fill=255)

    return mask


def random_gradient():
    return random.choice([
        ((40, 0, 70), (120, 0, 160)),
        ((0, 40, 60), (0, 120, 180)),
        ((60, 10, 0), (200, 60, 0)),
        ((10, 0, 30), (80, 0, 150)),
    ])


def apply_gradient(img, colors):
    c1, c2 = colors
    w, h = img.size
    base = Image.new("RGBA", (w, h), c1)
    top  = Image.new("RGBA", (w, h), c2)

    mask = Image.new("L", (w, h))
    md = ImageDraw.Draw(mask)

    for y in range(h):
        md.line([(0, y), (w, y)], fill=int(255 * (y / h)))

    return Image.composite(top, base, mask)


def random_layout():
    return {
        "art_size": random.randint(350, 420),
        "art_x": random.randint(80, 200),
        "art_shape": random.choice(["circle", "rounded"]),
        "text_align": random.choice(["left", "right"]),
    }


def random_accent_color():
    return random.choice([
        (255, 90, 90),
        (255, 160, 60),
        (100, 230, 255),
        (255, 60, 220),
        (160, 255, 80),
    ])


# ---------------- MAIN FUNCTION ----------------
async def get_thumb(videoid: str):

    # Default values (Fix - prevents UnboundLocalError)
    title    = "Unknown Title"
    duration = "0:00"
    views    = "0 Views"
    channel  = "Unknown Channel"
    thumb_path = None

    # ----------- FETCH YOUTUBE DATA -----------
    try:
        url = f"https://www.youtube.com/watch?v={videoid}"
        search = VideosSearch(url, limit=1)
        result = (await search.next())["result"][0]

        title    = result.get("title", title)
        duration = result.get("duration", duration)
        views    = result.get("viewCount", {}).get("short", views)
        channel  = result.get("channel", {}).get("name", channel)

        t_url = result["thumbnails"][0]["url"].split("?")[0]

        async with aiohttp.ClientSession() as session:
            async with session.get(t_url) as resp:
                if resp.status == 200:
                    thumb_path = CACHE_DIR / f"{videoid}.png"
                    async with aiofiles.open(thumb_path, "wb") as f:
                        await f.write(await resp.read())

        base_img = Image.open(thumb_path).convert("RGBA")

    except Exception:
        print("YouTube fetch failed - using default.")
        base_img = Image.open(DEFAULT_THUMB).convert("RGBA")

    # ----------- CREATE CANVAS -----------
    try:
        canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0))
        canvas = apply_gradient(canvas, random_gradient())

        layout = random_layout()
        accent = random_accent_color()

        # Paste cover art
        size = layout["art_size"]
        art = base_img.resize((size, size))
        mask = create_shape_mask(size, layout["art_shape"])

        art_y = (CANVAS_H - size) // 2
        canvas.paste(art, (layout["art_x"], art_y), mask)

        draw = ImageDraw.Draw(canvas)

        # ---- TEXT ----
        txt_x = 720 if layout["text_align"] == "right" else 50
        txt_y = 180

        title_font = ImageFont.truetype(FONT_BOLD_PATH, 46)
        lines = wrap_text(draw, title, title_font, 650)
        draw.multiline_text((txt_x, txt_y), "\n".join(lines),
                            fill=(255, 255, 255), font=title_font)

        meta_font = ImageFont.truetype(FONT_REGULAR_PATH, 32)
        draw.text((txt_x, txt_y + 150), views,    fill=(240, 240, 240), font=meta_font)
        draw.text((txt_x, txt_y + 200), duration, fill=(230, 230, 230), font=meta_font)
        draw.text((txt_x, txt_y + 250), channel,  fill=(220, 220, 220), font=meta_font)

        # Save output
        out = CACHE_DIR / f"{videoid}_final.png"
        canvas.save(out, optimize=True)

        return str(out)

    except Exception as e:
        traceback.print_exc()
        print("Thumbnail generation failed:", e)
        return None
