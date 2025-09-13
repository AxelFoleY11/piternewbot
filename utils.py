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
_download_counts = {}  # {user_id: {"count": int, "date": str}}
_analytics = {
    "total_users": set(),
    "subscribed_users": set(),
    "daily_downloads": {},  # {date: count}
    "user_activity": {},    # {user_id: {"first_seen": date, "last_seen": date, "total_downloads": int}}
}

# Система контроля нагрузки
_active_downloads = set()  # Множество активных скачиваний

def can_start_download(user_id: int) -> bool:
    """Проверить, можно ли начать новое скачивание"""
    import config
    return len(_active_downloads) < config.MAX_CONCURRENT_DOWNLOADS

def start_download(user_id: int) -> bool:
    """Начать отслеживание скачивания"""
    if can_start_download(user_id):
        _active_downloads.add(user_id)
        return True
    return False

def finish_download(user_id: int):
    """Завершить отслеживание скачивания"""
    _active_downloads.discard(user_id)

def get_system_load() -> dict:
    """Получить информацию о нагрузке системы"""
    return {
        "active_downloads": len(_active_downloads),
        "max_concurrent": config.MAX_CONCURRENT_DOWNLOADS,
        "load_percentage": (len(_active_downloads) / config.MAX_CONCURRENT_DOWNLOADS) * 100
    }


# --- аналитика ---
def track_user_activity(user_id: int, action: str = "visit"):
    """Отслеживать активность пользователя"""
    today = _get_today_date()
    
    # Добавляем пользователя в общую статистику
    _analytics["total_users"].add(user_id)
    
    # Обновляем активность пользователя
    if user_id not in _analytics["user_activity"]:
        _analytics["user_activity"][user_id] = {
            "first_seen": today,
            "last_seen": today,
            "total_downloads": 0,
            "subscription_status": False
        }
    else:
        _analytics["user_activity"][user_id]["last_seen"] = today
    
    # Обновляем ежедневную статистику
    if today not in _analytics["daily_downloads"]:
        _analytics["daily_downloads"][today] = 0

def track_subscription(user_id: int, is_subscribed: bool):
    """Отслеживать статус подписки"""
    if is_subscribed:
        _analytics["subscribed_users"].add(user_id)
        if user_id in _analytics["user_activity"]:
            _analytics["user_activity"][user_id]["subscription_status"] = True
    else:
        _analytics["subscribed_users"].discard(user_id)
        if user_id in _analytics["user_activity"]:
            _analytics["user_activity"][user_id]["subscription_status"] = False

def track_download(user_id: int):
    """Отслеживать скачивание"""
    today = _get_today_date()
    
    # Увеличиваем счетчик ежедневных скачиваний
    if today not in _analytics["daily_downloads"]:
        _analytics["daily_downloads"][today] = 0
    _analytics["daily_downloads"][today] += 1
    
    # Обновляем статистику пользователя
    if user_id in _analytics["user_activity"]:
        _analytics["user_activity"][user_id]["total_downloads"] += 1

def get_analytics_summary():
    """Получить сводку аналитики"""
    today = _get_today_date()
    
    # Статистика пользователей
    total_users = len(_analytics["total_users"])
    subscribed_users = len(_analytics["subscribed_users"])
    subscription_rate = (subscribed_users / total_users * 100) if total_users > 0 else 0
    
    # Статистика скачиваний
    today_downloads = _analytics["daily_downloads"].get(today, 0)
    total_downloads = sum(_analytics["daily_downloads"].values())
    
    # Активные пользователи (за последние 7 дней)
    active_users = 0
    for user_data in _analytics["user_activity"].values():
        if user_data["last_seen"] == today:
            active_users += 1
    
    return {
        "total_users": total_users,
        "subscribed_users": subscribed_users,
        "subscription_rate": round(subscription_rate, 1),
        "today_downloads": today_downloads,
        "total_downloads": total_downloads,
        "active_users_today": active_users,
        "daily_stats": dict(_analytics["daily_downloads"])
    }

def get_user_stats(user_id: int):
    """Получить статистику конкретного пользователя"""
    if user_id not in _analytics["user_activity"]:
        return None
    
    user_data = _analytics["user_activity"][user_id]
    return {
        "user_id": user_id,
        "first_seen": user_data["first_seen"],
        "last_seen": user_data["last_seen"],
        "total_downloads": user_data["total_downloads"],
        "is_subscribed": user_data["subscription_status"]
    }


# --- ограничения скачиваний ---
def _get_today_date():
    """Получить текущую дату в формате YYYY-MM-DD"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")

def _reset_daily_counts():
    """Сбросить счетчики скачиваний для всех пользователей"""
    today = _get_today_date()
    for user_id in list(_download_counts.keys()):
        if _download_counts[user_id]["date"] != today:
            del _download_counts[user_id]

def get_user_download_count(user_id: int) -> int:
    """Получить количество скачиваний пользователя за сегодня"""
    _reset_daily_counts()
    today = _get_today_date()
    
    if user_id not in _download_counts:
        _download_counts[user_id] = {"count": 0, "date": today}
    elif _download_counts[user_id]["date"] != today:
        _download_counts[user_id] = {"count": 0, "date": today}
    
    return _download_counts[user_id]["count"]

def increment_download_count(user_id: int) -> int:
    """Увеличить счетчик скачиваний пользователя"""
    _reset_daily_counts()
    today = _get_today_date()
    
    if user_id not in _download_counts:
        _download_counts[user_id] = {"count": 1, "date": today}
    elif _download_counts[user_id]["date"] != today:
        _download_counts[user_id] = {"count": 1, "date": today}
    else:
        _download_counts[user_id]["count"] += 1
    
    # Отслеживаем скачивание в аналитике
    track_download(user_id)
    
    return _download_counts[user_id]["count"]

def can_user_download(user_id: int, max_downloads: int = 5) -> bool:
    """Проверить, может ли пользователь скачать видео"""
    return get_user_download_count(user_id) < max_downloads

def get_remaining_downloads(user_id: int, max_downloads: int = 5) -> int:
    """Получить количество оставшихся скачиваний"""
    return max(0, max_downloads - get_user_download_count(user_id))


# --- кеш подписки ---
def _check_cache(user_id: int):
    if user_id in _subscription_cache:
        is_sub, ts = _subscription_cache[user_id]
        if time.time() - ts < config.CACHE_TIMEOUT:
            return is_sub
    return None


def _set_cache(user_id: int, is_sub: bool):
    _subscription_cache[user_id] = (is_sub, time.time())


async def check_subscription(user_id: int, context) -> bool:
    """
    Проверка подписки на каналы из config.CHANNELS
    """
    cached = _check_cache(user_id)
    if cached is not None:
        return cached

    try:
        for ch in config.CHANNELS:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                _set_cache(user_id, False)
                track_subscription(user_id, False)
                return False
        _set_cache(user_id, True)
        track_subscription(user_id, True)
        return True
    except Exception as e:
        logger.warning(f"Ошибка проверки подписки: {e}")
        _set_cache(user_id, False)
        track_subscription(user_id, False)
        return False


# --- нормализация ссылок ---
def normalize_video_url(url: str) -> str | None:
    if not url:
        return None
    url = url.strip()
    lower = url.lower()

    if "youtube.com/shorts/" in lower:
        video_id = url.split("shorts/")[-1].split("?")[0].split("/")[0]
        return f"https://www.youtube.com/watch?v={video_id}"

    if "youtu.be/" in lower:
        video_id = url.split("youtu.be/")[-1].split("?")[0].split("/")[0]
        return f"https://www.youtube.com/watch?v={video_id}"

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


# --- доступные качества ---
def get_available_qualities(url: str) -> list[int]:
    """
    Получить список доступных качеств для видео
    """
    try:
        # Создаем временный экземпляр yt-dlp для получения информации
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "listformats": True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info or 'formats' not in info:
                # Если не удалось получить информацию, возвращаем стандартные качества
                return [480, 720, 1080]
            
            # Извлекаем доступные разрешения
            available_heights = set()
            for fmt in info['formats']:
                if fmt.get('height') and fmt.get('vcodec') != 'none':
                    available_heights.add(fmt['height'])
            
            # Сортируем и фильтруем качества
            heights = sorted([h for h in available_heights if h >= 360], reverse=True)
            
            # Возвращаем до 3 лучших качеств
            if not heights:
                return [480, 720, 1080]  # Fallback
            
            # Выбираем лучшие доступные качества
            selected = []
            for target in [1080, 720, 480]:
                for height in heights:
                    if height >= target and target not in selected:
                        selected.append(target)
                        break
            
            return selected if selected else [heights[0]] if heights else [720]
            
    except Exception as e:
        logger.warning(f"Не удалось получить доступные качества: {e}")
        # Возвращаем стандартные качества в случае ошибки
        return [480, 720, 1080]


# --- скачивание видео ---
def download_video(url: str, quality: str, user_id: int = None) -> str:
    try:
        height = int(quality)
    except Exception:
        height = 720

    # Проверяем нагрузку системы
    if user_id and not can_start_download(user_id):
        raise Exception("Система перегружена. Попробуйте позже.")

    # Начинаем отслеживание скачивания
    if user_id:
        start_download(user_id)

    os.makedirs("downloads", exist_ok=True)

    ydl_opts = {
        # Улучшенная логика выбора качества - сначала ищем точное качество, потом лучшее доступное
        "format": f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/bestvideo+bestaudio/best",
        "outtmpl": "downloads/%(id)s_%(height)sp.%(ext)s",
        "merge_output_format": "mp4",
        "ffmpeg_location": config.FFMPEG_PATH,
        "noplaylist": True,
        "quiet": True,
        # Увеличиваем лимит размера файла для лучшего качества
        "max_filesize": config.MAX_FILE_SIZE * 2,  # Удваиваем лимит для качества
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        },
        "geo_bypass": True,
        "nocheckcertificate": True,
        "retries": 5,
        "socket_timeout": 60,
        "extractor_retries": 3,
        "fragment_retries": 5,
        "skip_unavailable_fragments": True,
        "keep_fragments": True,
        "extract_flat": False,
        "writethumbnail": False,
        "writeinfojson": False,
        "ignoreerrors": False,
        "no_color": True,
        "prefer_insecure": False,
        "legacy_server_connect": True,
        # Дополнительные настройки для лучшего качества
        "format_sort": ["res", "ext:mp4:m4a", "proto:https", "proto:http"],
        "format_sort_force": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                raise Exception("Не удалось получить информацию о видео")
                
            filename = ydl.prepare_filename(info)
            mp4_name = os.path.splitext(filename)[0] + ".mp4"
            
            # Проверяем, какой файл был создан
            if os.path.exists(mp4_name):
                if user_id:
                    finish_download(user_id)
                return mp4_name
            elif os.path.exists(filename):
                if user_id:
                    finish_download(user_id)
                return filename
            else:
                if user_id:
                    finish_download(user_id)
                raise Exception("Файл не был создан")
                
    except Exception as e:
        logger.error(f"Ошибка скачивания видео: {e}")
        
        # Попробуем альтернативный метод с другими настройками
        logger.info("Пробуем альтернативный метод скачивания...")
        try:
            alt_opts = ydl_opts.copy()
            alt_opts.update({
                # Более агрессивная стратегия для альтернативного метода
                "format": f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best",
                "extract_flat": False,
                "writethumbnail": False,
                "writeinfojson": False,
                "ignoreerrors": True,
                "no_color": True,
                "prefer_insecure": True,
                "legacy_server_connect": False,
                # Дополнительные настройки для альтернативного метода
                "format_sort": ["res", "ext:mp4:m4a", "proto:https", "proto:http"],
                "format_sort_force": True,
            })
            
            with yt_dlp.YoutubeDL(alt_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    raise Exception("Не удалось получить информацию о видео (альтернативный метод)")
                    
                filename = ydl.prepare_filename(info)
                mp4_name = os.path.splitext(filename)[0] + ".mp4"
                
                if os.path.exists(mp4_name):
                    if user_id:
                        finish_download(user_id)
                    return mp4_name
                elif os.path.exists(filename):
                    if user_id:
                        finish_download(user_id)
                    return filename
                else:
                    if user_id:
                        finish_download(user_id)
                    raise Exception("Файл не был создан (альтернативный метод)")
                    
        except Exception as alt_e:
            logger.error(f"Альтернативный метод также не сработал: {alt_e}")
            if user_id:
                finish_download(user_id)
            raise e
    except Exception as e:
        if user_id:
            finish_download(user_id)
        raise e


# --- клавиатуры ---
def subscription_keyboard():
    buttons = [
        [InlineKeyboardButton(f"🔔 {ch}", url=f"https://t.me/{ch.replace('@','')}")]
        for ch in config.CHANNELS
    ]
    buttons.append([InlineKeyboardButton("✅ Я подписался", callback_data="check_subscription")])
    return InlineKeyboardMarkup(buttons)


def quality_keyboard(url: str, user_id: int):
    video_id = str(uuid.uuid4())[:8]
    URL_CACHE[video_id] = url
    qualities = get_available_qualities(url)
    
    # Получаем информацию о лимитах
    remaining = get_remaining_downloads(user_id, config.MAX_DAILY_DOWNLOADS)
    
    # Создаем кнопки в одну строку
    buttons = []
    row = []
    for q in qualities:
        # Добавляем эмодзи в зависимости от качества
        emoji = "🔥" if q >= 1080 else "⭐" if q >= 720 else "📹"
        row.append(InlineKeyboardButton(f"{emoji} {q}p", callback_data=f"quality_{q}_{video_id}"))
    buttons.append(row)
    
    return InlineKeyboardMarkup(buttons), remaining


def pop_cached_url(video_id: str):
    return URL_CACHE.get(video_id)
