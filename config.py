import os
from dotenv import load_dotenv
import shutil

# Загружаем переменные из .env
ENV_PATH = "/root/piternewbot/.env"
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

# Конфигурация бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
TOKEN = BOT_TOKEN  # ← добавлено для совместимости со старым кодом

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(2000 * 1024 * 1024)))  # 2GB

# Каналы
CHANNELS = ["@it_begin", "@it_begin_books", "@ITtechnologyPCNeuralnetworks"]

# Автоматическое определение пути к FFmpeg
FFMPEG_PATH = FFMPEG_PATH = FFMPEG_PATH = r"C:\ffmpeg-2025-09-08-git-45db6945e9-essentials_build\bin\ffmpeg.exe"



# Проверка токена при запуске
if not BOT_TOKEN:
    print("⚠️ BOT_TOKEN не найден! Проверь .env")
