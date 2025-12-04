import os
import aiohttp
import aiofiles
import traceback
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from youtubesearchpython.__future__ import VideosSearch
from XMUSIC.core.dir import CACHE_DIR
from config import YOUTUBE_IMG_URL

# ---------------- CONSTANTS ----------------
CANVAS_W, CANVAS_H = 1280, 720
BG_BLUR = 18
BG_BRIGHTNESS = 0.85

TEXT_WHITE = (255, 255, 255, 255)
TEXT_SOFT = (240, 240, 240, 255)
TEXT_SHADOW = (0, 0, 0, 180)

FONT_REGULAR = "XMUSIC/assets/thumb/font.ttf"
FONT_BOLD = "XMUSIC/assets/thumb/font2.ttf"
DEFAULT_THUMB = "XMUSIC/assets/thumb/default.png"

# Ensure CACHE_DIR is a Path object
CACHE_DIR = Path(CACHE_DIR)
CACHE_DIR.mkdir(exist_ok=True)

# ---------------- UTILITIES ----------------
def change_image_size(max_w, max_h, image):
    ratio = min(max_w / image.size[0], max_h / image.size[1])
    return image.resize((int(image.size[0]*ratio), int(image.size[1]*ratio)), Image.LANCZOS)

def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        if draw.textlength(test_line, font=font) <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines[:2]

def get_vibrant_edge_color(image):
    img_small = image.resize((100, 100), Image.LANCZOS)
    pixels = list(img_small.getdata())
    edge_pixels = []
    size = 100
    for i in range(size):
        edge_pixels.append(pixels[i])
        edge_pixels.append(pixels[i * size])
        edge_pixels.append(pixels[(i + 1) * size - 1])
        edge_pixels.append(pixels[size * (size - 1) + i])
    r_avg = sum(p[0] for p in edge_pixels) // len(edge_pixels)
    g_avg = sum(p[1] for p in edge_pixels) // len(edge_pixels)
    b_avg = sum(p[2] for p in edge_pixels) // len(edge_pixels)
    return (r_avg, g_avg, b_avg, 255)

def create_premium_glow(size, glow_color, intensity=1.0):
    glow = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    layers = [
        (0, int(180 * intensity)),
        (15, int(140 * intensity)),
        (30, int(100 * intensity)),
        (45, int(70 * intensity)),
        (60, int(40 * intensity)),
        (75, int(20 * intensity))
    ]
    for offset, alpha in layers:
        color = (*glow_color[:3], alpha)
        draw.rectangle(
            [offset, offset, size[0]-offset, size[1]-offset],
            outline=color,
            width=int(15 + (offset/10))
        )
    return glow.filter(ImageFilter.GaussianBlur(25))

# ---------------- MAIN FUNCTION ----------------
async def get_thumb(videoid: str):
    url = f"https://www.youtube.com/watch?v={videoid}"
    thumb_path = None
    
    # Fetch YouTube data
    try:
        results = VideosSearch(url, limit=1)
        result = (await results.next())["result"][0]
        title = result.get("title", "Unknown Title")
        duration = result.get("duration") or "Live"
        thumburl = result["thumbnails"][0]["url"].split("?")[0]
        views = result.get("viewCount", {}).get("short", "0 views")
        channel = result.get("channel", {}).get("name", "Unknown Channel")
    except:
        title, duration, views, channel = "Unknown", "Live", "0 views", "XMUSIC"
        thumburl = YOUTUBE_IMG_URL

    # Download thumbnail
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumburl) as resp:
                if resp.status == 200:
                    thumb_path = CACHE_DIR / f"thumb_{videoid}.png"
                    async with aiofiles.open(thumb_path, "wb") as f:
                        await f.write(await resp.read())
    except:
        thumb_path = None

    # Open base image
    try:
        if thumb_path and thumb_path.exists():
            base_img = Image.open(thumb_path).convert("RGBA")
        else:
            base_img = Image.open(DEFAULT_THUMB).convert("RGBA")
    except:
        base_img = Image.new("RGBA", (CANVAS_W, CANVAS_H), (30, 30, 30, 255))

    # Create background
    bg = change_image_size(CANVAS_W, CANVAS_H, base_img).filter(ImageFilter.GaussianBlur(BG_BLUR))
    bg = ImageEnhance.Brightness(bg).enhance(BG_BRIGHTNESS)

    # Frosted overlay gradient
    overlay = Image.new("RGBA", bg.size, (0,0,0,0))
    draw_overlay = ImageDraw.Draw(overlay)
    for i in range(150):
        alpha = int((i/150)*100)
        draw_overlay.rectangle([(0, CANVAS_H-150+i), (CANVAS_W, CANVAS_H-150+i+1)], fill=(0,0,0,alpha))
    bg = Image.alpha_composite(bg, overlay)

    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0,0,0,255))
    canvas.paste(bg, (0,0))

    # Glow layer
    edge_color = get_vibrant_edge_color(base_img)
    glow_layer = create_premium_glow((CANVAS_W, CANVAS_H), edge_color, intensity=1.2)
    canvas = Image.alpha_composite(canvas, glow_layer)

    draw = ImageDraw.Draw(canvas)

    # Circular thumbnail
    thumb_size = 360
    circle_x, circle_y = 60, (CANVAS_H-thumb_size)//2
    circular_mask = Image.new("L", (thumb_size, thumb_size), 0)
    ImageDraw.Draw(circular_mask).ellipse((0,0,thumb_size,thumb_size), fill=255)
    art = base_img.resize((thumb_size, thumb_size), Image.LANCZOS)
    art.putalpha(circular_mask)
    canvas.paste(art, (circle_x, circle_y), art)

    # Text: NOW PLAYING
    np_font = ImageFont.truetype(FONT_BOLD, 70)
    np_text = "NOW PLAYING"
    np_x = circle_x + thumb_size + 40
    np_y = 120
    shadow_offset = 4
    draw.text((np_x+shadow_offset,np_y+shadow_offset), np_text, fill=TEXT_SHADOW, font=np_font)
    draw.text((np_x,np_y), np_text, fill=TEXT_WHITE, font=np_font)

    # Title
    title_font = ImageFont.truetype(FONT_BOLD, 40)
    title_lines = wrap_text(draw, title, title_font, CANVAS_W - np_x - 60)
    title_text = "\n".join(title_lines)
    title_y = np_y + 100
    draw.multiline_text((np_x+3,title_y+3), title_text, fill=TEXT_SHADOW, font=title_font, spacing=10)
    draw.multiline_text((np_x,title_y), title_text, fill=TEXT_WHITE, font=title_font, spacing=10)

    # Metadata
    meta_font = ImageFont.truetype(FONT_REGULAR, 28)
    meta_y_start = title_y + 120
    for i, meta in enumerate([f"Views: {views}", f"Duration: {duration}", f"Channel: {channel}"]):
        y = meta_y_start + i*40
        draw.text((np_x+2,y+2), meta, fill=TEXT_SHADOW, font=meta_font)
        draw.text((np_x,y), meta, fill=TEXT_SOFT, font=meta_font)

    out_path = CACHE_DIR / f"{videoid}_xmusic.png"
    canvas.save(out_path, quality=95, optimize=True)

    # Clean up
    if thumb_path and thumb_path.exists():
        try: os.remove(thumb_path)
        except: pass

    return str(out_path)
