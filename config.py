import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Ограничения
TELEGRAM_LIMIT = 2 * 1024 * 1024 * 1024   # 2 GB
MAX_FILE_SIZE = 500 * 1024 * 1024         # 500 MB

# Каналы для обязательной подписки
CHANNELS = ["@it_begin", "@it_begin_books", "@ITtechnologyPCNeuralnetworks"]

# ffmpeg (если в PATH, просто "ffmpeg")
FFMPEG_PATH = "ffmpeg"

# Таймаут кэша подписки
CACHE_TIMEOUT = 300

# Ограничения скачиваний
MAX_DAILY_DOWNLOADS = 5

# Ограничения для Cloud MSK 40 (2 CPU, 2GB RAM, 40GB SSD)
MAX_CONCURRENT_DOWNLOADS = 2  # Максимум 2 одновременных скачивания
MAX_FILE_SIZE = 400 * 1024 * 1024  # 400MB для лучшего качества (было 200MB)
CLEANUP_INTERVAL = 3600  # Очистка временных файлов каждый час
