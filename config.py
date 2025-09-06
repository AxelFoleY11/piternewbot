import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Конфигурация бота
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 123456789))
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "/usr/bin/ffmpeg")
MAX_FILE_SIZE = 50 * 1024 * 1024

CHANNELS = ["@it_begin", "@it_begin_books", "@ITtechnologyPCNeuralnetworks"]
