import os

# Токен бота
BOT_TOKEN = os.getenv("8474046690:AAFdXt4xAu4OjWqipEibPc8kRP3nfXSCvo0")

# ID админа (чтобы показывать кнопку "связаться")
ADMIN_ID = os.getenv("ADMIN_ID", "973384981")

# Лимит файла для Telegram (2 ГБ = 2 * 1024 * 1024 * 1024)
TELEGRAM_LIMIT = 2 * 1024 * 1024 * 1024

# Максимальный размер скачиваемого файла (например 500 МБ)
MAX_FILE_SIZE = 500 * 1024 * 1024

# Каналы для подписки (если не нужно — оставь пустой список)
CHANNELS = []

# Где искать ffmpeg (если установлен глобально — оставить просто "ffmpeg")
FFMPEG_PATH = "ffmpeg"

# Таймаут кэша подписки (в секундах)
CACHE_TIMEOUT = 300
