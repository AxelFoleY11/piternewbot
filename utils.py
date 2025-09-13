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


# --- подписка ---
def _check_cache(user_id: int):
    if user_id in _subscription_cache:
        is_sub, ts = _subscription_cache[user_id]
        if time.time() - ts < config.CACHE_TIMEOUT:
            return is_sub
    return None


def _set_cache(user_id: int, is_sub: bool):
    _subscription_cache[user_id] = (is_sub, time.time())


async def check_subscription(user_id: int, context) -> bool:
    cached = _check_cache(user_id)
    if cached is not None:
        return cached

    try:
        for ch in config.CHANNELS:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                _set_cache(user_id, False)
                return False
        _set_cache(user_id, True)
        return True
    except Exception as e:
        logger.warning(f"Ошибка проверки подписки: {e}")
        _set_cache(user_id, False)
        return False


# --- ссылки ---
def normalize_video_url(url: str) -> str | None:
    if not url:
        return None
    url = url.strip()

    lower = url.lower()

    # YouTube shorts → watch?v=
    if "youtube.com/shorts/" in lower:
        video_id = url.split("shorts/")[-1].split("?")[0].split("/")[0]
        return f"https://www.youtube.com/watch?v={video_id}"

    # youtu.be → watch?v=
    if "youtu.be/" in lower:
        video_id = url.split("youtu.be/")[-1].split("?")[0].split("/")[0]
        return f"https://www.youtube.com/watch?v={video_id}"

    # embed → watch?v=
    if "youtube.com/embed/" in lower:
        video_id = url.split("embed/")[-1].split("?")[0].split("/")[0]
        return f"https://www.youtube.com/watch?v={video_id}"

    if "youtube.com/watch" in lower:
        return url.split("&")[0]

    if "tiktok.com" in lower:
        return url.split("?")[0]

    if "instagram.com" in lower and any(x in lower for x in ["/reel/", "/p/", "/tv/"]):
        return url.split("?")[0]

    if any(x in lower for x in ["vk.com", "vimeo.com", "dailymotion.com"]):
        return url.split("?")[0]

    return None


# --- качества ---
def get_available_qualities(url: str) -> list[int]:
    ydl_opts = {"quiet": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            heights = {f.get("height") for f in info.get("formats", []) if f.get("height")}
            allowed = [360, 480, 720, 1080]
            available = sorted(h for h in heights if h in allowed)
            return available if available else [720]
    except Exception as e:
        logger.warning(f"Ошибка yt-dlp: {e}")
        return [720]


# --- скачивание ---
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


# --- клавиатуры ---
def subscription_keyboard():
    buttons = [
        [InlineKeyboardButton(f"🔔 {ch}", url=f"https://t.me/{ch.replace('@','')}")]
        for ch in config.CHANNELS
    ]
    buttons.append([InlineKeyboardButton("✅ Я подписался", callback_data="check_subscription")])
    return InlineKeyboardMarkup(buttons)


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
