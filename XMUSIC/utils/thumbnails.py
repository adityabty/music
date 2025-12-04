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

# Removed create_premium_glow as we are using direct drawing for neon ring

# Utility function to convert seconds to MM:SS format
def secs_to_m_s(seconds):
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
        # A robust parsing logic should handle PT, H, M, S format (e.g., using isodate or custom regex)
        # Keeping your simple parsing logic here, but cautioning about its fragility
        if "M" in duration_str and "S" in duration_str:
            parts = duration_str.split('M')
            minutes = int(parts[0].replace('PT', '').replace('H', '0'))
            seconds = int(parts[1].replace('S', ''))
            return (minutes * 60) + seconds
        elif "M" in duration_str:
             minutes = int(duration_str.split('M')[0].replace('PT', ''))
             return minutes * 60
        elif duration_str.isdigit():
             return int(duration_str)
    except:
        pass
    return TOTAL_DURATION_SECS

# ---------------- MAIN FUNCTION ----------------
async def get_thumb(videoid: str):
    # url = f"https://www.youtube.com/watch?v={videoid}" # Using videoid directly for search is better
    thumb_path = None
    
    # --- Time Setup ---
    # Setting to 90 seconds (01:30) to show the progress bar handle, matching your generated image
    CURRENT_TIME_SECS = 90  
    TOTAL_DURATION_SECS = 272 

    # Fetch YouTube data
    try:
        # Use videoid directly for robust search
        results = VideosSearch(videoid, limit=1)
        result = (await results.next())["result"][0]
        title = result.get("title", "Unknown Title")
        duration_str = result.get("duration") or "Live"
        
        TOTAL_DURATION_SECS = get_total_duration_secs(duration_str)
        
        duration_display = secs_to_m_s(TOTAL_DURATION_SECS) if TOTAL_DURATION_SECS > 0 else "Live"
        
        thumburl = result["thumbnails"][0]["url"].split("?")[0]
        views = result.get("viewCount", {}).get("short", "0 views")
        channel = result.get("channel", {}).get("name", "Unknown Channel")
    except Exception as e:
        # Default data used if YouTube fetch fails
        print(f"ERROR: YouTube data fetch failed: {e}")
        title, duration_display, views, channel = "My Awesome Music Track", "04:32", "1.2M views", "MusicChannel"
        thumburl = YOUTUBE_IMG_URL
        TOTAL_DURATION_SECS = 272 
        
    CURRENT_TIME_SECS = min(CURRENT_TIME_SECS, TOTAL_DURATION_SECS) # Clamp current time
    current_time_display = secs_to_m_s(CURRENT_TIME_SECS)
    
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

    # **FIXED SECTION:** Open base image with better fallback for visibility
    try:
        if thumb_path and thumb_path.exists():
            base_img = Image.open(thumb_path).convert("RGBA")
        else:
            base_img = Image.open(DEFAULT_THUMB).convert("RGBA")
    except Exception as e:
        # If download and DEFAULT_THUMB fail, use a clearly visible WHITE fallback image
        print(f"ERROR: Image loading failed (Downloaded or Default). Using WHITE fallback. Error: {e}")
        # Create a large white image that will be visible when cropped to a circle
        base_img = Image.new("RGBA", (CANVAS_W, CANVAS_H), (255, 255, 255, 255)) 

    # Create background
    bg = change_image_size(CANVAS_W, CANVAS_H, base_img).filter(ImageFilter.GaussianBlur(BG_BLUR))
    bg = ImageEnhance.Brightness(bg).enhance(BG_BRIGHTNESS)

    # Frosted overlay gradient (Optional, to darken the bottom)
    overlay = Image.new("RGBA", bg.size, (0,0,0,0))
    draw_overlay = ImageDraw.Draw(overlay)
    for i in range(150):
        alpha = int((i/150)*100)
        draw_overlay.rectangle([(0, CANVAS_H-150+i), (CANVAS_W, CANVAS_H-150+i+1)], fill=(0,0,0,alpha))
    bg = Image.alpha_composite(bg, overlay)

    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0,0,0,255))
    canvas.paste(bg, (0,0))
    draw = ImageDraw.Draw(canvas)

    # Circular thumbnail
    thumb_size = 360
    circle_x, circle_y = 100, (CANVAS_H-thumb_size)//2
    circular_mask = Image.new("L", (thumb_size, thumb_size), 0)
    ImageDraw.Draw(circular_mask).ellipse((0,0,thumb_size,thumb_size), fill=255)
    
    art = base_img.resize((thumb_size, thumb_size), Image.LANCZOS)
    art.putalpha(circular_mask)
    
    # Paste the circular art (Profile Picture)
    canvas.paste(art, (circle_x, circle_y), art)
    
    # --- RED NEON GLOW FOR CIRCULAR THUMBNAIL ---
    GLOW_COLOR = (255, 30, 0, 255) # Deep Red

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

    # --- TEXT METADATA ---
    np_font = ImageFont.truetype(FONT_BOLD, 40)
    title_font = ImageFont.truetype(FONT_BOLD, 75)
    meta_font = ImageFont.truetype(FONT_REGULAR, 32)

    np_x = circle_x + thumb_size + 80
    
    # Text: NOW PLAYING
    np_text = "NOW PLAYING"
    np_y = 140
    draw.text((np_x, np_y), np_text, fill=TEXT_WHITE, font=np_font)

    # Title
    title_y = np_y + 60
    title_lines = wrap_text(draw, title, title_font, CANVAS_W - np_x - 60)
    title_text = "\n".join(title_lines)
    draw.multiline_text((np_x, title_y), title_text, fill=TEXT_WHITE, font=title_font, spacing=10)

    # Metadata (Views and Channel)
    meta_y_start = title_y + len(title_lines) * 85 + 20
    
    # Views
    views_text = f"Views: {views}"
    draw.text((np_x, meta_y_start), views_text, fill=TEXT_SOFT, font=meta_font)
    
    # Channel
    channel_text = f"Channel: {channel}"
    draw.text((np_x, meta_y_start + 45), channel_text, fill=TEXT_SOFT, font=meta_font)

    # --- SPOTIFY-LIKE TIME STRAP / PROGRESS BAR ---
    
    # Layout constants for the progress bar
    BAR_Y = CANVAS_H - 100
    BAR_MARGIN = 60
    BAR_START_X = BAR_MARGIN + 100
    BAR_END_X = CANVAS_W - BAR_MARGIN - 100
    BAR_WIDTH = BAR_END_X - BAR_START_X
    BAR_HEIGHT = 8
    
    # Progress calculation
    progress_ratio = CURRENT_TIME_SECS / TOTAL_DURATION_SECS if TOTAL_DURATION_SECS else 0
    progress_end_x = BAR_START_X + int(BAR_WIDTH * progress_ratio)
    
    # Colors
    BAR_BG_COLOR = (255, 255, 255, 100) # Light grey, transparent
    BAR_FG_COLOR = (255, 0, 0, 255)     # Red (matching the neon glow)
    BAR_HANDLE_SIZE = 12

    # Draw background bar (Unplayed part)
    draw.rectangle([BAR_START_X, BAR_Y, BAR_END_X, BAR_Y + BAR_HEIGHT], fill=BAR_BG_COLOR)
    
    # Draw foreground bar (Played part)
    draw.rectangle([BAR_START_X, BAR_Y, progress_end_x, BAR_Y + BAR_HEIGHT], fill=BAR_FG_COLOR)
    
    # Draw a circle/handle at the current position (Played part)
    if CURRENT_TIME_SECS > 0: # Only draw handle if progress is past 00:00
        draw.ellipse([
            progress_end_x - BAR_HANDLE_SIZE/2, 
            BAR_Y + BAR_HEIGHT/2 - BAR_HANDLE_SIZE/2, 
            progress_end_x + BAR_HANDLE_SIZE/2, 
            BAR_Y + BAR_HEIGHT/2 + BAR_HANDLE_SIZE/2
        ], fill=BAR_FG_COLOR)

    # Time text below the bar
    time_font = ImageFont.truetype(FONT_REGULAR, 24)
    time_y = BAR_Y + BAR_HEIGHT + 10
    
    # Current Time (Left)
    draw.text((BAR_START_X, time_y), current_time_display, fill=TEXT_WHITE, font=time_font)
    
    # Total Duration (Right)
    total_time_width = draw.textlength(duration_display, font=time_font)
    draw.text((BAR_END_X - total_time_width, time_y), duration_display, fill=TEXT_WHITE, font=time_font)


    out_path = CACHE_DIR / f"{videoid}_xmusic.png"
    canvas.save(out_path, quality=95, optimize=True)

    # Clean up
    if thumb_path and thumb_path.exists():
        try: os.remove(thumb_path)
        except: pass

    return str(out_path)
        
