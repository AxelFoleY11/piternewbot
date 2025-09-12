# utils.py
import yt_dlp
import os
import time
import uuid
import logging
from urllib.parse import urlparse, parse_qs
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
import config

logger = logging.getLogger(__name__)

# Кэш URL и подписок
URL_CACHE = {}
subscription_cache = {}


# --- Подписка ---
def check_cache(user_id: int):
    if user_id in subscription_cache:
        is_subscribed, ts = subscription_cache[user_id]
        if time.time() - ts < config.CACHE_TIMEOUT:
            return is_subscribed
    return None


def set_cache(user_id: int, is_subscribed: bool):
    subscription_cache[user_id] = (is_subscribed, time.time())


async def check_subscription(user_id: int, context) -> bool:
    cached = check_cache(user_id)
    if cached is not None:
        return cached
    try:
        for channel in config.CHANNELS:
            try:
                # Используем именованные параметры для явности
                member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    set_cache(user_id, False)
                    return False
            except Exception as e:
                logger.warning(f"Ошибка проверки {channel}: {e}")
                # Если одна из проверок неудачна — считаем пользователя не подписанным
                set_cache(user_id, False)
                return False
        set_cache(user_id, True)
        return True
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {e}")
        set_cache(user_id, False)
        return False


# --- Нормализация ссылок ---
def normalize_video_url(url: str) -> str | None:
    """
    Нормализует ссылку:
      - youtube.com/shorts/ID -> https://www.youtube.com/watch?v=ID
      - youtu.be/ID -> https://www.youtube.com/watch?v=ID
      - vm.tiktok.com (и другие короткие TikTok) — возвращаем как есть, yt-dlp разрулит редирект
      - instagram /p/ /reel/ /tv/ -> без параметров
      - остальные оставляем как есть (vk, vimeo, dailymotion и т.д.)
    """
    if not url:
        return None
    url = url.strip()

    lower = url.lower()

    # YouTube Shorts → watch?v=
    if "youtube.com/shorts/" in lower:
        # Берём реальную часть после shorts/
        video_id = url.split("shorts/")[-1].split("?")[0].split("/")[0]
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"

    # youtu.be → watch?v=
    if "youtu.be/" in lower:
        video_id = url.split("youtu.be/")[-1].split("?")[0].split("/")[0]
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"

    # Обычный YouTube watch?v=
    if "youtube.com/watch" in lower or "youtube.com/watch?" in lower:
        return url.split("&")[0]  # отрезаем дополнительные параметры

    # TikTok short links (vm, vt) и обычные tiktok ссылки — yt-dlp справится с редиректами
    if "vm.tiktok.com" in lower or "vt.tiktok.com" in lower or "tiktok.com" in lower:
        return url.split("?")[0]

    # Instagram
    if "instagram.com" in lower and ("/reel/" in lower or "/p/" in lower or "/tv/" in lower):
        return url.split("?")[0]

    # VK, Vimeo, Dailymotion - возвращаем как есть
    if "vk.com" in lower or "vimeo.com" in lower or "dailymotion.com" in lower:
        return url.split("?")[0]

    # Неизвестный формат
    return None


# --- Качества ---
def get_available_qualities(url: str) -> list[int]:
    """Возвращает список доступных качеств (высота в px)."""
    ydl_opts = {"quiet": True, "skip_download": True}
    qualities = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            for f in info.get("formats", []):
                if f.get("height"):
                    qualities.append(int(f["height"]))
        qualities = sorted(set(qualities))
        # Оставляем только полезные значения
        allowed = [360, 480, 720, 1080, 1440, 2160]
        return [q for q in qualities if q in allowed]
    except Exception as e:
        logger.error(f"Ошибка получения форматов для {url}: {e}")
        # По умолчанию возвращаем 720p
        return [720]


# --- Скачивание ---
def download_video(url: str, quality: str) -> str:
    """
    Скачивает видео с помощью yt-dlp в указанной высоте (например "720" или "1080").
    Возвращает путь к файлу.
    """
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
        # небольшие улучшения на постпроцессинг
        "postprocessor_args": ["-threads", "4"],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # Если merge_output_format создал .mp4 рядом с оригинальным именем, используем .mp4
            mp4_name = os.path.splitext(filename)[0] + ".mp4"
            if os.path.exists(mp4_name):
                return mp4_name
            return filename
    except Exception as e:
        logger.error(f"Ошибка скачивания {url}: {e}")
        raise Exception("⚠️ Не удалось скачать видео")


# --- Клавиатуры ---
def subscription_keyboard():
    buttons = [
        [InlineKeyboardButton(f"🔔 {ch}", url=f"https://t.me/{ch.replace('@','')}")]
        for ch in config.CHANNELS
    ]
    buttons.append([InlineKeyboardButton("✅ Я подписался", callback_data="check_subscription")])
    return InlineKeyboardMarkup(buttons)


def quality_keyboard(url: str):
    """
    Формирует InlineKeyboard с доступными качествами.
    Сохраняет URL в URL_CACHE под случайным id.
    """
    video_id = str(uuid.uuid4())[:8]
    URL_CACHE[video_id] = url

    qualities = get_available_qualities(url)

    # Если yt-dlp не вернул ничего полезного, добавим 720
    if not qualities:
        qualities = [720]

    buttons = []
    row = []
    for q in qualities:
        row.append(InlineKeyboardButton(f"{q}p", callback_data=f"quality_{q}_{video_id}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)
