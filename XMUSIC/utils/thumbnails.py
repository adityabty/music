import os
import re
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from youtubesearchpython.__future__ import VideosSearch
from config import YOUTUBE_IMG_URL
from XMUSIC.core.dir import CACHE_DIR


# ---------------- UI CONSTANTS ----------------
PANEL_W, PANEL_H = 880, 360
PANEL_X = (1280 - PANEL_W) // 2
PANEL_Y = 180

TRANSPARENCY = 160
INNER_OFFSET = 25

THUMB_W, THUMB_H = 160, 160
THUMB_X = PANEL_X + 40
THUMB_Y = PANEL_Y + 100

TITLE_X = THUMB_X + THUMB_W + 40
META_X = TITLE_X
TITLE_Y = THUMB_Y + 10
META_Y = TITLE_Y + 50

BAR_X = TITLE_X
BAR_Y = META_Y + 50
BAR_RED_LEN = 200
BAR_TOTAL_LEN = 400

MAX_TITLE_WIDTH = 430

WATERMARK = "XMUSIC"


# ---------------- Title Trimming ----------------
def trim_to_width(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> str:
    ellipsis = "…"
    if font.getlength(text) <= max_w:
        return text
    for i in range(len(text) - 1, 0, -1):
        if font.getlength(text[:i] + ellipsis) <= max_w:
            return text[:i] + ellipsis
    return ellipsis


# ---------------- Main Generator ----------------
async def get_thumb(videoid: str) -> str:
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_xmusic.png")
    if os.path.exists(cache_path):
        return cache_path

    # ------------- Fetch YouTube Data -------------
    results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
    try:
        results_data = await results.next()
        item = results_data["result"][0]

        title = item.get("title", "Unknown Title")
        thumbnail = item.get("thumbnails", [{}])[0].get("url", YOUTUBE_IMG_URL)
        duration = item.get("duration")
        views = item.get("viewCount", {}).get("short", "0 views")

    except Exception:
        title, thumbnail, duration, views = "Unknown", YOUTUBE_IMG_URL, None, "0 views"

    is_live = not duration or str(duration).lower() in ["live", "live now"]
    duration_text = "Live" if is_live else duration

    # ------------- Download Thumbnail -------------
    thumb_path = os.path.join(CACHE_DIR, f"_t{videoid}.png")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    async with aiofiles.open(thumb_path, "wb") as f:
                        await f.write(await resp.read())
    except:
        return YOUTUBE_IMG_URL

    # ------------- Background Blur -------------
    base = Image.open(thumb_path).resize((1280, 720)).convert("RGBA")
    bg = ImageEnhance.Brightness(base.filter(ImageFilter.GaussianBlur(12))).enhance(0.6)

    # ------------- Frosted Panel -------------
    panel = Image.new("RGBA", (PANEL_W, PANEL_H), (255, 255, 255, TRANSPARENCY))
    mask = Image.new("L", (PANEL_W, PANEL_H), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, PANEL_W, PANEL_H), 50, fill=255)
    bg.paste(panel, (PANEL_X, PANEL_Y), mask)

    draw = ImageDraw.Draw(bg)

    # Fonts
    try:
        title_font = ImageFont.truetype("XMUSIC/assets/thumb/font2.ttf", 45)
        meta_font = ImageFont.truetype("XMUSIC/assets/thumb/font.ttf", 24)
    except:
        title_font = meta_font = ImageFont.load_default()

    # ------------- Small Thumbnail -------------
    small = Image.open(thumb_path).resize((THUMB_W, THUMB_H))
    sm_mask = Image.new("L", (THUMB_W, THUMB_H), 0)
    ImageDraw.Draw(sm_mask).rounded_rectangle((0, 0, THUMB_W, THUMB_H), 30, fill=255)
    bg.paste(small, (THUMB_X, THUMB_Y), sm_mask)

    # ------------- Text -------------
    draw.text((TITLE_X, TITLE_Y), trim_to_width(title, title_font, MAX_TITLE_WIDTH), fill="white", font=title_font)
    draw.text((META_X, META_Y), f"{views}", fill="white", font=meta_font)

    # ------------- Progress Bar -------------
    draw.line([(BAR_X, BAR_Y), (BAR_X + BAR_RED_LEN, BAR_Y)], fill=(255, 80, 80), width=8)
    draw.line([(BAR_X + BAR_RED_LEN, BAR_Y), (BAR_X + BAR_TOTAL_LEN, BAR_Y)], fill="gray", width=6)
    draw.ellipse([(BAR_X + BAR_RED_LEN - 10, BAR_Y - 10),
                  (BAR_X + BAR_RED_LEN + 10, BAR_Y + 10)], fill="red")

    draw.text((BAR_X, BAR_Y + 15), "00:00", fill="white", font=meta_font)
    draw.text((BAR_X + BAR_TOTAL_LEN - 80, BAR_Y + 15), duration_text, fill="white", font=meta_font)

    # ------------- Watermark XMUSIC -------------
    draw.text((1050, 670), "@XMUSIC", fill="white", font=meta_font)

    bg.save(cache_path)

    os.remove(thumb_path)
    return cache_path
