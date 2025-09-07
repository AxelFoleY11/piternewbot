
import os
from dotenv import load_dotenv
import time

# Загружаем переменные из .env
load_dotenv()

# Конфигурация бота
TOKEN = os.getenv('TELEGRAM_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 123456789))

CHANNELS = ["@it_begin", "@it_begin_books", "@ITtechnologyPCNeuralnetworks"]
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Автоматическое определение пути к FFmpeg
import shutil
FFMPEG_PATH = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"

# Кеш подписок
SUBSCRIPTION_CACHE = {}
CACHE_TIMEOUT = 300  # 5 минут
