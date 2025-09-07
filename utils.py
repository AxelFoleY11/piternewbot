import yt_dlp
import os
import config
import time
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def check_cache(user_id: int) -> bool:
    """Проверяет кеш подписки"""
    if user_id in config.SUBSCRIPTION_CACHE:
        is_subscribed, timestamp = config.SUBSCRIPTION_CACHE[user_id]
        if time.time() - timestamp < config.CACHE_TIMEOUT:
            return is_subscribed
    return None

def set_cache(user_id: int, is_subscribed: bool):
    """Устанавливает кеш подписки"""
    config.SUBSCRIPTION_CACHE[user_id] = (is_subscribed, time.time())

async def check_subscription(user_id: int, context) -> bool:
    """Проверяет подписку на все каналы с кешированием"""
    # Проверяем кеш
    cached_result = check_cache(user_id)
    if cached_result is not None:
        return cached_result
    
    try:
        for channel in config.CHANNELS:
            try:
                member = await context.bot.get_chat_member(
                    chat_id=channel, 
                    user_id=user_id
                )
                if member.status not in ["member", "administrator", "creator"]:
                    set_cache(user_id, False)
                    return False
            except Exception as e:
                print(f"Ошибка проверки канала {channel}: {e}")
                continue
        
        set_cache(user_id, True)
        return True
        
    except Exception as e:
        print(f"Общая ошибка проверки подписки: {e}")
        set_cache(user_id, False)
        return False

def download_video(url: str, quality: str) -> str:
    """Скачивает видео с выбранным качеством"""
    height = {
        "720": 720,
        "1080": 1080,
        "2160": 2160
    }.get(quality, 720)
    
    ydl_opts = {
        "format": f"bestvideo[height<={height}]+bestaudio/best[height<={height}]",
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "merge_output_format": "mp4",
        "ffmpeg_location": config.FFMPEG_PATH,
        "quiet": False,
        "noplaylist": True,
        "max_filesize": config.MAX_FILE_SIZE,
        "postprocessor_args": ["-threads", "4"]
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    except Exception as e:
        raise Exception(f"Ошибка скачивания: {str(e)}")

def subscription_keyboard():
    """Создает клавиатуру для подписки на каналы"""
    buttons = []
    for channel in config.CHANNELS:
        channel_name = channel.replace('@', '')
        buttons.append([
            InlineKeyboardButton(
                f"🔔 {channel}", 
                url=f"https://t.me/{channel_name}"
            )
        ])
    buttons.append([
        InlineKeyboardButton("✅ Я подписался", callback_data="check_subscription")
    ])
    return InlineKeyboardMarkup(buttons)

def quality_keyboard(url: str):
    """Создает клавиатуру выбора качества"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("720p", callback_data=f"quality_720_{url}"),
            InlineKeyboardButton("1080p", callback_data=f"quality_1080_{url}"),
        ],
        [
            InlineKeyboardButton("4K (2160p)", callback_data=f"quality_2160_{url}")
        ]
    ])
