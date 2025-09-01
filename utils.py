import yt_dlp
import os
import config
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

async def check_subscription(user_id: int, context) -> bool:
    """Проверяет подписку на все каналы"""
    for channel in config.CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except Exception as e:
            print(f"Ошибка проверки канала {channel}: {e}")
            return False
    return True

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
        "quiet": True,
        "noplaylist": True,
        "max_filesize": config.MAX_FILE_SIZE,
        "postprocessor_args": {
            "default": ["-threads", "4"]
        }
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

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
