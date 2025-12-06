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

# FONT paths - Make sure these paths are correct in your environment
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
    # Sampling edge pixels
    for i in range(size):
        edge_pixels.append(pixels[i])
        edge_pixels.append(pixels[i * size])
        edge_pixels.append(pixels[(i + 1) * size - 1])
        edge_pixels.append(pixels[size * (size - 1) + i])
    # Calculate average RGB
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

# Utility function to convert seconds to MM:SS format
def secs_to_m_s(seconds):
    try:
        seconds = int(seconds)
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    except:
        return "00:00"

# ---------------- MAIN FUNCTION ----------------
async def gen_thumb(videoid: str):
    url = f"https://www.youtube.com/watch?v={videoid}"
    thumb_path = None
    
    try:
        results = VideosSearch(url, limit=1)
        result = (await results.next())["result"][0]

        title = result.get("title", "Unknown Title")
        duration = result.get("duration", "Unknown")
        thumburl = result["thumbnails"][0]["url"].split("?")[0]
        views = result.get("viewCount", {}).get("short", "Unknown Views")
        channel = result.get("channel", {}).get("name", "Unknown Channel")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(thumburl) as resp:
                    if resp.status == 200:
                        thumb_path = CACHE_DIR / f"thumb{videoid}.png"
                        async with aiofiles.open(thumb_path, "wb") as f:
                            await f.write(await resp.read())
        except:
            pass

        if thumb_path and thumb_path.exists():
            base_img = Image.open(thumb_path).convert("RGBA")
        else:
            base_img = Image.open(DEFAULT_THUMB).convert("RGBA")

    except Exception as e:
        print(f"[gen_thumb Error - Using Default] {e}")
        try:
            base_img = Image.open(DEFAULT_THUMB).convert("RGBA")
            title = "ShrutiMusic"
            duration = "Unknown"
            views = "Unknown Views"
            channel = "ShrutiBots"
        except:
            traceback.print_exc()
            return None

    try:
        canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 255))
        
        gradient_colors = random_gradient()
        canvas = apply_gradient(canvas, gradient_colors)
        
        layout = random_layout()
        accent_color = random_accent_color()
        
        if layout['show_particles']:
            draw = ImageDraw.Draw(canvas)
            add_particles(draw, accent_color)
            canvas = canvas.filter(ImageFilter.GaussianBlur(1))
        
        art_size = layout['art_size']
        art_x = layout['art_x']
        art_y = (CANVAS_H - art_size) // 2
        
        mask = create_shape_mask(art_size, layout['art_shape'])
        art = base_img.resize((art_size, art_size), Image.LANCZOS)
        art.putalpha(mask)
        
        if random.choice([True, False]):
            add_glow_ring(canvas, art_x, art_y, art_size, accent_color, random.randint(8, 15))
        
        canvas.paste(art, (art_x, art_y), art)
        
        draw = ImageDraw.Draw(canvas)
        
        add_accent_elements(draw, layout, accent_color)
        
        brand_font = ImageFont.truetype(FONT_BOLD_PATH, random.randint(36, 48))
        brand_x = random.randint(35, 60)
        brand_y = random.randint(25, 45)
        
        shadow_offset = 2
        draw.text((brand_x + shadow_offset, brand_y + shadow_offset), 
                 app.username, fill=(0, 0, 0, 150), font=brand_font)
        draw.text((brand_x, brand_y), app.username, fill=(255, 255, 255, 255), font=brand_font)
        
        brand_bbox = draw.textbbox((brand_x, brand_y), app.username, font=brand_font)
        brand_w = brand_bbox[2] - brand_bbox[0]
        underline_y = brand_bbox[3] + 6
        draw.line([(brand_x, underline_y), (brand_x + brand_w, underline_y)], 
                 fill=(*accent_color, 200), width=3)
        
        if layout['text_align'] == 'right':
            info_x = art_x + art_size + random.randint(60, 100)
            max_text_w = CANVAS_W - info_x - 50
        else:
            info_x = random.randint(50, 100)
            max_text_w = art_x - info_x - 50
        
        np_options = ["NOW PLAYING", "PLAYING NOW", "NOW PLAYING", "PLAYING"]
        np_font = ImageFont.truetype(FONT_BOLD_PATH, random.randint(50, 70))
        np_text = random.choice(np_options)
        np_y = random.randint(120, 160)
        
        np_shadow = 3
        draw.text((info_x + np_shadow, np_y + np_shadow), np_text, 
                 fill=(0, 0, 0, 180), font=np_font)
        draw.text((info_x, np_y), np_text, fill=(*accent_color, 255), font=np_font)
        
        title_font_size = random.randint(36, 48)
        title_font = ImageFont.truetype(FONT_BOLD_PATH, title_font_size)
        title_lines = wrap_text(draw, title, title_font, max_text_w)
        title_text = "\n".join(title_lines)
        title_y = np_y + random.randint(70, 100)
        
        title_shadow = 2
        draw.multiline_text((info_x + title_shadow, title_y + title_shadow), title_text, 
                          fill=(0, 0, 0, 160), font=title_font, 
                          spacing=random.randint(8, 15))
        draw.multiline_text((info_x, title_y), title_text, 
                          fill=(255, 255, 255, 255), font=title_font, 
                          spacing=random.randint(8, 15))
        
        meta_font = ImageFont.truetype(FONT_REGULAR_PATH, random.randint(28, 36))
        meta_y = title_y + random.randint(120, 160)
        line_spacing = random.randint(45, 60)
        
        duration_label = duration
        if duration and ":" in duration:
            parts = duration.split(":")
            if len(parts) == 2 and parts[0].isdigit():
                duration_label = f"{parts[0]}m {parts[1]}s"
        
        meta_labels = random.choice([
            ["Views", "Duration", "Channel"],
            ["", "", ""]
        ])
        
        meta_items = [
            f"{meta_labels[0]} {views}" if meta_labels[0] else f"{views}",
            f"{meta_labels[1]} {duration_label}" if meta_labels[1] else f"{duration_label}",
            f"{meta_labels[2]} {channel}" if meta_labels[2] else f"{channel}"
        ]
        
        for idx, meta in enumerate(meta_items):
            y = meta_y + (idx * line_spacing)
            draw.text((info_x + 1, y + 1), meta, fill=(0, 0, 0, 140), font=meta_font)
            draw.text((info_x, y), meta, fill=(220, 220, 230, 255), font=meta_font)
        
        if random.choice([True, False]):
            corner_size = random.randint(30, 50)
            corner_width = random.randint(2, 4)
            corner_color = (*accent_color, 120)
            
            draw.line([(25, 25), (25 + corner_size, 25)], fill=corner_color, width=corner_width)
            draw.line([(25, 25), (25, 25 + corner_size)], fill=corner_color, width=corner_width)
            
            draw.line([(CANVAS_W - 25, 25), (CANVAS_W - 25 - corner_size, 25)], 
                     fill=corner_color, width=corner_width)
            draw.line([(CANVAS_W - 25, 25), (CANVAS_W - 25, 25 + corner_size)], 
                     fill=corner_color, width=corner_width)
        
        out = CACHE_DIR / f"{videoid}_final.png"
        canvas.save(out, quality=95, optimize=True)

        if thumb_path and thumb_path.exists():
            try:
                os.remove(thumb_path)
            except:
                pass

        return str(out)

    except Exception as e:
        print(f"[gen_thumb Processing Error] {e}")
        traceback.print_exc()
        return None
