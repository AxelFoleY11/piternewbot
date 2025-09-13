import os
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import utils, config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if await utils.check_subscription(user.id, context):
        await update.message.reply_text("👋 Привет! Отправь ссылку на видео.")
    else:
        await update.message.reply_text(
            "📢 Подпишись на каналы, чтобы использовать бота:",
            reply_markup=utils.subscription_keyboard()
        )


# --- обработка ссылок ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await utils.check_subscription(user.id, context):
        await update.message.reply_text(
            "❌ Сначала подпишись на каналы:",
            reply_markup=utils.subscription_keyboard()
        )
        return

    url = (update.message.text or "").strip()
    norm = utils.normalize_video_url(url)

    if not norm:
        await update.message.reply_text(
            "⚠️ Неверная ссылка!\n\n"
            "Поддерживаемые форматы:\n"
            "• YouTube: https://youtube.com/watch?v=...\n"
            "• Shorts / youtu.be / embed\n"
            "• TikTok: https://tiktok.com/@user/video/...\n"
            "• Instagram: /reel/, /p/, /tv/\n"
            "• VK, Vimeo, Dailymotion"
        )
        return

    kb = utils.quality_keyboard(norm)
    await update.message.reply_text("🎬 Выберите качество:", reply_markup=kb)


# --- inline кнопки ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "check_subscription":
        if await utils.check_subscription(query.from_user.id, context):
            await query.edit_message_text("✅ Подписка подтверждена! Отправь ссылку на видео.")
        else:
            await query.answer("❌ Вы не подписаны!", show_alert=True)
        return

    if not data.startswith("quality_"):
        return

    _, q, vid = data.split("_")
    url = utils.pop_cached_url(vid)

    if not url:
        await query.edit_message_text("⚠️ Ошибка: ссылка устарела")
        return

    if not await utils.check_subscription(query.from_user.id, context):
        await query.edit_message_text("❌ Подписка обязательна.")
        return

    try:
        await query.edit_message_text(f"⏳ Скачиваю в {q}p...")
        file_path = utils.download_video(url, q)

        if os.path.getsize(file_path) > config.TELEGRAM_LIMIT:
            await query.edit_message_text("⚠️ Файл слишком большой для Telegram (>2 ГБ)")
            return

        await query.message.reply_video(video=open(file_path, "rb"))
        await query.edit_message_text("✅ Видео отправлено.")

        try:
            os.remove(file_path)
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Ошибка скачивания: {e}")
        await query.edit_message_text(f"❌ Ошибка: {e}")


def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button))
    print("✅ Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
