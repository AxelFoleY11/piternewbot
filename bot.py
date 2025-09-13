import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import utils, config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Команда /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Отправь ссылку на видео (YouTube, Shorts, TikTok, Instagram, VK, Vimeo, Dailymotion)."
    )

# --- Обработка текста (ссылки) ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    norm = utils.normalize_video_url(url)

    if not norm:
        await update.message.reply_text(
            "⚠️ Неверная ссылка!\n\nПоддерживаемые форматы:\n"
            "• YouTube: https://youtube.com/watch?v=...\n"
            "• TikTok: https://tiktok.com/@user/video/123...\n"
            "• Instagram: https://instagram.com/p/...\n"
            "• VK, Vimeo, Dailymotion"
        )
        return

    kb = utils.quality_keyboard(norm)
    await update.message.reply_text("🎬 Выберите качество:", reply_markup=kb)

# --- Обработка выбора качества ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("quality_"):
        return

    _, q, vid = data.split("_")
    url = utils.pop_cached_url(vid)

    if not url:
        await query.edit_message_text("⚠️ Ошибка: ссылка устарела")
        return

    try:
        await query.edit_message_text("⏳ Скачиваю видео...")
        file_path = utils.download_video(url, q)

        if os.path.getsize(file_path) > config.TELEGRAM_LIMIT:
            await query.edit_message_text("⚠️ Файл слишком большой для Telegram (>2 ГБ)")
            return

        await query.message.reply_video(video=open(file_path, "rb"))
    except Exception as e:
        logger.error(f"Ошибка скачивания: {e}")
        await query.edit_message_text(f"❌ Ошибка: {e}")

# --- Запуск ---
def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button))
    print("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
