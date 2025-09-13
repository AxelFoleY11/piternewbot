import yt_dlp
import os
import time
import uuid
import logging
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
import config

logger = logging.getLogger(__name__)

URL_CACHE = {}
_subscription_cache = {}

# --- Нормализация ссылок ---
def normalize_video_url(url: str) -> str | None:
    if not url:
        return None
    url = url.strip().lower()

    # YouTube Shorts → watch?v=
    if "youtube.com/shorts/" in url:
        video_id = url.split("shorts/")[-1].split("?")[0].split("/")[0]
        return f"https://www.youtube.com/watch?v={video_id}"

    # youtu.be → watch?v=
    if "youtu.be/" in url:
        video_id = url.split("youtu.be/")[-1].split("?")[0].split("/")[0]
        return f"https://www.youtube.com/watch?v={video_id}"

    # embed
    if "youtube.com/embed/" in url:
        video_id = url.split("embed/")[-1].split("?")[0].split("/")[0]
        return f"https://www.youtube.com/watch?v={video_id}"

    # обычный YouTube watch
    if "youtube.com/watch" in url:
        return url.split("&")[0]

    # TikTok
    if "tiktok.com" in url:
        return url.split("?")[0]

    # Instagram
    if "instagram.com" in url and any(x in url for x in ["/reel/", "/p/", "/tv/"]):
        return url.split("?")[0]

    # VK, Vimeo, Dailymotion
    if any(x in url for x in ["vk.com", "vimeo.com", "dailymotion.com"]):
        return url.split("?")[0]

    return None


# --- Качества ---
def get_available_qualities(url: str) -> list[int]:
    ydl_opts = {"quiet": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            heights = {f.get("height") for f in info.get("formats", []) if f.get("height")}
            allowed = [360, 480, 720, 1080]  # ⚡️ без 4K
            available = sorted(h for h in heights if h in allowed)
            return available if available else [720]
    except Exception as e:
        logger.warning(f"get_available_qualities failed: {e}")
        return [720]


# --- Скачивание ---
def download_video(url: str, quality: str) -> str:
    try:
        height = int(quality)
    except Exception:
        height = 720

    os.makedirs("downloads", exist_ok=True)

    ydl_opts = {
        "format": f"bestvideo[height<={height}]+bestaudio/best[height<={height}]",
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "merge_output_format": "mp4",
        "ffmpeg_location": config.FFMPEG_PATH,
        "noplaylist": True,
        "quiet": True,
        "max_filesize": config.MAX_FILE_SIZE,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        mp4_name = os.path.splitext(filename)[0] + ".mp4"
        return mp4_name if os.path.exists(mp4_name) else filename


# --- Клавиатуры ---
def quality_keyboard(url: str):
    video_id = str(uuid.uuid4())[:8]
    URL_CACHE[video_id] = url
    qualities = get_available_qualities(url)
    rows, row = [], []
    for q in qualities:
        row.append(InlineKeyboardButton(f"{q}p", callback_data=f"quality_{q}_{video_id}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def pop_cached_url(video_id: str):
    return URL_CACHE.get(video_id)
