
# a part of Opus Music Project 2025 ©
# this code is & will be our property as it is or even after modified 
# must give credits if used this code anywhere 
import os
import re
import textwrap
import numpy as np
import aiofiles
import aiohttp
from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
)
from youtubesearchpython.__future__ import VideosSearch
from config import YOUTUBE_IMG_URL
def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    ratio = min(widthRatio, heightRatio)
    newWidth = int(image.size[0] * ratio)
    newHeight = int(image.size[1] * ratio)
    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:
        resample = Image.ANTIALIAS  # For Pillow<10
    image = image.resize((newWidth, newHeight), resample)
    return image
def get_dominant_color(image):
    """Extract the dominant color from the image"""
    # Convert to RGB if not already
    image = image.convert('RGB')
    
    # Resize to speed up processing
    image = image.resize((50, 50))
    
    # Get all pixels
    pixels = np.array(image)
    
    # Reshape to get list of RGB values
    pixel_list = pixels.reshape(-1, 3)
    
    # Calculate average color
    avg_color = tuple(pixel_list.mean(axis=0).astype(int))
    
    # Ensure color is bright enough for visibility
    # If too dark, brighten it
    if sum(avg_color) < 200:  # If color is too dark
        brightened = tuple(min(255, int(c * 1.5)) for c in avg_color)
        return brightened
    
    return avg_color
def get_contrasting_color(bg_color):
    """Get a contrasting color for better visibility"""
    # Calculate luminance
    luminance = (0.299 * bg_color[0] + 0.587 * bg_color[1] + 0.114 * bg_color[2])
    
    # Return white for dark backgrounds, dark for light backgrounds
    return (255, 255, 255) if luminance < 128 else (50, 50, 50)
async def get_thumb(videoid):
    final_path = f"cache/{videoid}.png"
    if os.path.isfile(final_path):
        return final_path
    url = f"https://www.youtube.com/watch?v={videoid}"
    try:
        results = VideosSearch(url, limit=1)
        result_data = await results.next()
        if not result_data.get("result"):
            return YOUTUBE_IMG_URL
        result = result_data["result"][0]
        title = re.sub(r"\W+", " ", result.get("title", "Unknown Title")).title()
        duration = result.get("duration", "Unknown Duration")
        thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        views = result.get("viewCount", {}).get("short", "Unknown Views")
        channel = result.get("channel", {}).get("name", "Unknown Channel")
        # Ensure cache directory exists
        os.makedirs("cache", exist_ok=True)
        # Download thumbnail
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                thumb_path = f"cache/thumb{videoid}.png"
                async with aiofiles.open(thumb_path, mode="wb") as f:
                    await f.write(await resp.read())
        # Verify downloaded file is a valid image
        try:
            youtube = Image.open(thumb_path)
        except:
            os.remove(thumb_path) if os.path.exists(thumb_path) else None
            return YOUTUBE_IMG_URL
        # Extract dominant color from thumbnail for duration bar
        bar_color = get_dominant_color(youtube)
        
        image1 = changeImageSize(1280, 720, youtube.copy())
        center_thumb = changeImageSize(940, 420, youtube.copy())
        # Rounded center image mask
        mask = Image.new("L", center_thumb.size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.rounded_rectangle(
            [0, 0, center_thumb.size[0], center_thumb.size[1]],
            radius=40,
            fill=255
        )
        # Background blur (softer)
        image2 = image1.convert("RGBA")
        background = image2.filter(ImageFilter.BoxBlur(18))
        background = ImageEnhance.Brightness(background).enhance(0.8)
        # Paste rounded thumbnail
        thumb_pos = (170, 90)
        center_thumb_rgba = center_thumb.convert("RGBA")
        background.paste(center_thumb_rgba, thumb_pos, mask)
        # Load fonts safely
        def safe_font(path, size):
            try:
                return ImageFont.truetype(path, size)
            except:
                return ImageFont.load_default()
        font = safe_font("OpusV/resources/font.ttf", 30)
        font2 = safe_font("OpusV/resources/font.ttf", 30)
        arial = safe_font("OpusV/resources/font2.ttf", 30)
        # Draw text
        draw = ImageDraw.Draw(background)
        # Channel | Views
        draw.text((50, 565), f"{channel} | {views[:23]}", fill="white", font=arial)
        # Title
        title = textwrap.shorten(title, width=50, placeholder="...")
        draw.text((50, 600), title, fill="white", font=font, stroke_fill="white")
        # Start and End Time
        draw.text((50, 640), "00:25", fill="white", font=font2, stroke_width=1, stroke_fill="grey")
        draw.text((1150, 640), duration[:23], fill="white", font=font2, stroke_width=1, stroke_fill="white")
        # Duration bar with auto color from thumbnail
        draw.line((150, 660, 1130, 660), width=6, fill=bar_color)
        # Recreation Music text at right side of center thumbnail
        rec_font = safe_font("OpusV/resources/font.ttf", 40)
        rec_text = "Recreation Music"
        bbox = draw.textbbox((0, 0), rec_text, font=rec_font)
        rec_text_w = bbox[2] - bbox[0]
        rec_text_h = bbox[3] - bbox[1]
        rec_x = thumb_pos[0] + center_thumb.width + 25
        rec_y = thumb_pos[1] + (center_thumb.height // 2) - (rec_text_h // 2)
        draw.text((rec_x, rec_y), rec_text, fill="white", font=rec_font)
        # Clean up temporary file
        try:
            os.remove(thumb_path)
        except:
            pass
        # Save final image
        background.save(final_path, format="PNG")
        return final_path
    except Exception:
        return YOUTUBE_IMG_URL
    
