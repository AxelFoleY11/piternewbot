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
