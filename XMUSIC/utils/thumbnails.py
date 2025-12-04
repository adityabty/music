import os
import aiohttp
import aiofiles
import traceback
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from youtubesearchpython.__future__ import VideosSearch

# Assuming these are defined in your config.py
from config import YOUTUBE_IMG_URL, CACHE_DIR 

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
DEFAULT_THUMB = "XMUSIC/assets/thumb/default.png" # Must be a valid image file!

# Ensure CACHE_DIR is a Path object
# Assuming CACHE_DIR is correctly defined and exists
CACHE_DIR = Path(CACHE_DIR)
CACHE_DIR.mkdir(exist_ok=True)

# ---------------- UTILITIES ----------------
def change_image_size(max_w, max_h, image):
    """Resizes image to fit within max_w and max_h while maintaining aspect ratio."""
    ratio = min(max_w / image.size[0], max_h / image.size[1])
    return image.resize((int(image.size[0]*ratio), int(image.size[1]*ratio)), Image.LANCZOS)

def wrap_text(draw, text, font, max_width):
    """Wraps text to fit within a max width, limiting to two lines."""
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

def secs_to_m_s(seconds):
    """Converts seconds to MM:SS format."""
    try:
        seconds = int(seconds)
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    except:
        return "00:00"

def get_total_duration_secs(duration_str):
    """Tries to parse YouTube duration string into total seconds."""
    TOTAL_DURATION_SECS = 272 # Default duration (4:32)
    try:
        # A simple parsing logic for demonstration (may need refinement based on exact API format)
        if "M" in duration_str and "S" in duration_str:
            parts = duration_str.split('M')
            minutes = int(parts[0].replace('PT', '').replace('H', '0'))
            seconds = int(parts[1].replace('S', ''))
            TOTAL_DURATION_SECS = (minutes * 60) + seconds
        elif "M" in duration_str:
             minutes = int(duration_str.split('M')[0].replace('PT', ''))
             TOTAL_DURATION_SECS = minutes * 60
        elif duration_str.isdigit():
             TOTAL_DURATION_SECS = int(duration_str)
    except:
        pass
    return TOTAL_DURATION_SECS

# ---------------- MAIN FUNCTION ----------------
async def get_thumb(videoid: str):
    url = f"https://www.youtube.com/watch?v={videoid}"
    thumb_path = None
    
    # --- Time Setup (Simulated Playback Progress) ---
    TOTAL_DURATION_SECS = 272 # Default to 4:32
    CURRENT_TIME_SECS = 0     # Start time (as in your image)

    # --- 1. Fetch YouTube data ---
    try:
        results = VideosSearch(videoid, limit=1) # Use videoid directly for search
        result = (await results.next())["result"][0]
        title = result.get("title", "Unknown Title")
        duration_str = result.get("duration") or "Live"
        
        TOTAL_DURATION_SECS = get_total_duration_secs(duration_str)
        
        duration_display = secs_to_m_s(TOTAL_DURATION_SECS) if TOTAL_DURATION_SECS > 0 else "Live"
        
        thumburl = result["thumbnails"][0]["url"].split("?")[0]
        views = result.get("viewCount", {}).get("short", "0 views")
        channel = result.get("channel", {}).get("name", "MusicChannel")
        
    except Exception as e:
        # Debug print for data fetch error
        print(f"ERROR: YouTube data fetch failed. Using defaults. Error: {e}")
        title, duration_display, views, channel = "My Awesome Music Track", "04:32", "1.2M views", "MusicChannel"
        thumburl = YOUTUBE_IMG_URL
        TOTAL_DURATION_SECS = 272 

    # --- 2. Download thumbnail ---
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumburl) as resp:
                if resp.status == 200:
                    thumb_path = CACHE_DIR / f"thumb_{videoid}.png"
                    async with aiofiles.open(thumb_path, "wb") as f:
                        await f.write(await resp.read())
                    # Debug print for successful download
                    # print(f"DEBUG: Thumbnail downloaded successfully to: {thumb_path}")
                else:
                    print(f"DEBUG: Download failed with status {resp.status}")
    except Exception as e:
        print(f"ERROR: Thumbnail download or save failed: {e}")
        thumb_path = None

    # --- 3. Open base image (Handles Fallback) ---
    try:
        if thumb_path and thumb_path.exists():
            base_img = Image.open(thumb_path).convert("RGBA")
        else:
            base_img = Image.open(DEFAULT_THUMB).convert("RGBA")
            # print(f"DEBUG: Falling back to default: {DEFAULT_THUMB}")
    except Exception as e:
        print(f"ERROR: Failed to open default image: {e}")
        base_img = Image.new("RGBA", (CANVAS_W, CANVAS_H), (30, 30, 30, 255))

    # --- 4. Setup Canvas and Background ---
    
    # Create background (Blurred and Darkened)
    bg = change_image_size(CANVAS_W, CANVAS_H, base_img).filter(ImageFilter.GaussianBlur(BG_BLUR))
    bg = ImageEnhance.Brightness(bg).enhance(BG_BRIGHTNESS)

    # Frosted overlay gradient (To darken the bottom)
    overlay = Image.new("RGBA", bg.size, (0,0,0,0))
    draw_overlay = ImageDraw.Draw(overlay)
    for i in range(150):
        alpha = int((i/150)*100)
        draw_overlay.rectangle([(0, CANVAS_H-150+i), (CANVAS_W, CANVAS_H-150+i+1)], fill=(0,0,0,alpha))
    bg = Image.alpha_composite(bg, overlay)

    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0,0,0,255))
    canvas.paste(bg, (0,0))
    draw = ImageDraw.Draw(canvas)

    # --- 5. Circular Thumbnail with Neon Glow ---
    thumb_size = 360
    circle_x, circle_y = 100, (CANVAS_H-thumb_size)//2
    GLOW_COLOR = (255, 30, 0, 255) # Deep Red

    # Circular Mask
    circular_mask = Image.new("L", (thumb_size, thumb_size), 0)
    ImageDraw.Draw(circular_mask).ellipse((0,0,thumb_size,thumb_size), fill=255)
    
    # Resize and mask the image
    art = base_img.resize((thumb_size, thumb_size), Image.LANCZOS)
    art.putalpha(circular_mask)
    
    # Paste the masked image
    canvas.paste(art, (circle_x, circle_y), art) 
    
    # Neon Glow Ring (Drawn directly on the canvas)
    glow_size = thumb_size + 15
    glow_x, glow_y = circle_x - 7, circle_y - 7
    
    # Draw a thin, slightly blurred red ring for the neon effect
    for i in range(1, 4):
        ring_color = (GLOW_COLOR[0], GLOW_COLOR[1], GLOW_COLOR[2], int(255 / (i * 1.5)))
        draw.ellipse((glow_x - i, glow_y - i, glow_x + glow_size + i, glow_y + glow_size + i), 
                     outline=ring_color, 
                     width=2)
    # Use a separate blurred image for a softer interior glow (optional but good)
    glow_inner = Image.new("RGBA", (glow_size + 20, glow_size + 20), (0, 0, 0, 0))
    draw_inner = ImageDraw.Draw(glow_inner)
    draw_inner.ellipse((10, 10, glow_size + 10, glow_size + 10), outline=GLOW_COLOR, width=10)
    glow_inner = glow_inner.filter(ImageFilter.GaussianBlur(12))
    canvas.paste(glow_inner, (glow_x - 10, glow_y - 10), glow_inner)

    # --- 6. Text Metadata ---
    np_font = ImageFont.truetype(FONT_BOLD, 45)
    title_font = ImageFont.truetype(FONT_BOLD, 70)
    meta_font = ImageFont.truetype(FONT_REGULAR, 32)

    np_x = circle_x + thumb_size + 80
    
    # NOW PLAYING
    np_text = "NOW PLAYING"
    np_y = 140
    draw.text((np_x, np_y), np_text, fill=TEXT_SOFT, font=np_font)

    # Title
    title_y = np_y + 70
    title_lines = wrap_text(draw, title, title_font, CANVAS_W - np_x - 60)
    title_text = "\n".join(title_lines)
    draw.multiline_text((np_x, title_y), title_text, fill=TEXT_WHITE, font=title_font, spacing=10)

    # Views and Channel
    meta_y_start = title_y + len(title_lines) * 80 + 20
    draw.text((np_x, meta_y_start), f"Views: {views}", fill=TEXT_SOFT, font=meta_font)
    draw.text((np_x, meta_y_start + 45), f"Channel: {channel}", fill=TEXT_SOFT, font=meta_font)

    # --- 7. Spotify-like Time Strap / Progress Bar ---
    
    BAR_Y = CANVAS_H - 100
    BAR_MARGIN = 100
    BAR_START_X = BAR_MARGIN 
    BAR_END_X = CANVAS_W - BAR_MARGIN
    BAR_WIDTH = BAR_END_X - BAR_START_X
    BAR_HEIGHT = 6
    
    # Progress is currently 00:00, so progress_end_x will be BAR_START_X
    progress_ratio = CURRENT_TIME_SECS / TOTAL_DURATION_SECS if TOTAL_DURATION_SECS > 0 else 0
    progress_end_x = BAR_START_X + int(BAR_WIDTH * progress_ratio)
    
    # Colors (Matching the red neon theme)
    BAR_BG_COLOR = (255, 255, 255, 100) # Light grey for unplayed
    BAR_FG_COLOR = (255, 0, 0, 255)     # Red for played
    
    # Draw background bar (Unplayed part - Grey)
    draw.rectangle([progress_end_x, BAR_Y, BAR_END_X, BAR_Y + BAR_HEIGHT], fill=BAR_BG_COLOR)
    
    # Draw foreground bar (Played part - Red)
    draw.rectangle([BAR_START_X, BAR_Y, progress_end_x, BAR_Y + BAR_HEIGHT], fill=BAR_FG_COLOR)
    
    # Time text below the bar
    time_font = ImageFont.truetype(FONT_REGULAR, 28)
    time_y = BAR_Y + BAR_HEIGHT + 10
    
    # Current Time (Left - 00:00 as per your image)
    draw.text((BAR_START_X, time_y), secs_to_m_s(CURRENT_TIME_SECS), fill=TEXT_WHITE, font=time_font)
    
    # Total Duration (Right - 4:32 as per your image)
    total_time_width = draw.textlength(duration_display, font=time_font)
    draw.text((BAR_END_X - total_time_width, time_y), duration_display, fill=TEXT_WHITE, font=time_font)

    # --- 8. Save and Cleanup ---
    out_path = CACHE_DIR / f"{videoid}_xmusic.png"
    canvas.save(out_path, quality=95, optimize=True)

    if thumb_path and thumb_path.exists():
        try: os.remove(thumb_path)
        except: pass

    return str(out_path)
            
