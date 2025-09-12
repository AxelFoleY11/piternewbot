# bot.py
# -*- coding: utf-8 -*-
import os
import asyncio
import logging
import traceback

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

import config
import utils

# --- Логирование ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# --- Команды ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if await utils.check_subscription(user.id, context):
        await update.message.reply_text(
            "🎬 Привет! Отправь ссылку на видео (YouTube, Shorts, TikTok, Instagram, VK, Vimeo, Dailymotion)."
        )
    else:
        await update.message.reply_text(
            "📢 Для использования бота подпишитесь на наши каналы:",
            reply_markup=utils.subscription_keyboard(),
        )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Отправь ссылку на видео — бот предложит качества и скачает mp4.\n\n"
        "✅ Поддерживается:\n"
        "• YouTube (включая Shorts, youtu.be)\n"
        "• TikTok (включая vm.tiktok.com)\n"
        "• Instagram (p, reel, tv)\n"
        "• VK, Vimeo, Dailymotion\n\n"
        "❌ Не поддерживаются: профили, плейлисты, поиск."
    )


# --- Обработка сообщений ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (update.message.text or "").strip()

    # Проверка подписки
    if not await utils.check_subscription(user.id, context):
        await update.message.reply_text(
            "❌ Доступ ограничен — подпишитесь на наши каналы:",
            reply_markup=utils.subscription_keyboard(),
        )
        return

    # Нормализация ссылки (обрабатывает shorts, youtu.be и т.д.)
    norm_url = utils.normalize_video_url(text)
    if not norm_url:
        await update.message.reply_text(
            "⚠️ Неверная ссылка!\n\n"
            "Поддерживаемые форматы:\n"
            "• YouTube: https://youtube.com/watch?v=...\n"
            "• Shorts / youtu.be\n"
            "• TikTok: https://tiktok.com/@user/video/123...\n"
            "• Instagram: https://instagram.com/p/... или /reel/...\n\n"
            "❌ Не принимаются: главные страницы, профили, поиск."
        )
        return

    try:
        # Генерация клавиатуры в пуле, т.к. yt-dlp может быть блокирующим.
        loop = asyncio.get_running_loop()
        kb = await loop.run_in_executor(None, utils.quality_keyboard, norm_url)
        await update.message.reply_text("🎬 Выберите качество:", reply_markup=kb)
    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры: {e}")
        await update.message.reply_text("⚠️ Не удалось определить доступные качества.")
        await notify_admin(
            context,
            f"Ошибка quality_keyboard у {user.id} @{getattr(user, 'username', None)}:\n{e}\n{traceback.format_exc()}",
        )


# --- Подтверждение подписки ---
async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await utils.check_subscription(query.from_user.id, context):
        await query.edit_message_text("✅ Подписка подтверждена! Отправьте ссылку на видео.")
    else:
        await query.answer("❌ Вы не подписаны на все каналы.", show_alert=True)


# --- Скачивание видео ---
async def handle_quality_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_", 2)
    if len(parts) < 3:
        await query.edit_message_text("⚠️ Некорректный запрос.")
        return

    _, quality, video_id = parts
    url = utils.URL_CACHE.get(video_id)
    if not url:
        await query.edit_message_text("⚠️ Сессия устарела. Пришлите ссылку ещё раз.")
        return

    # Проверка подписки
    if not await utils.check_subscription(query.from_user.id, context):
        await query.edit_message_text("❌ Вы отписались от каналов — доступ закрыт.")
        return

    await query.edit_message_text(f"⏳ Скачиваю в {quality}p...")

    try:
        loop = asyncio.get_running_loop()
        file_path = await loop.run_in_executor(None, utils.download_video, url, quality)

        if not os.path.exists(file_path):
            await query.edit_message_text("❌ Ошибка: файл не найден.")
            await notify_admin(context, f"Файл не найден для {url}")
            return

        with open(file_path, "rb") as f:
            await query.message.reply_video(video=f, caption=f"✅ Ваше видео {quality}p")

        try:
            os.remove(file_path)
        except Exception:
            pass

        await query.edit_message_text("✅ Видео отправлено.")
    except Exception as e:
        logger.error(f"Ошибка загрузки: {e}")
        await query.edit_message_text("⚠️ Не удалось скачать видео.")
        await notify_admin(
            context,
            f"Ошибка скачивания у {query.from_user.id} @{getattr(query.from_user, 'username', None)}:\n"
            f"URL: {url}\nError: {e}\n{traceback.format_exc()}",
        )


# --- Уведомление админа ---
async def notify_admin(context: ContextTypes.DEFAULT_TYPE, text: str):
    try:
        admin = getattr(config, "ADMIN_ID", 0)
        if admin and int(admin) != 0:
            await context.bot.send_message(chat_id=int(admin), text=f"⚠️ BOT ERROR\n{text}")
    except Exception as e:
        logger.error(f"Не удалось уведомить админа: {e}")


# --- Запуск ---
def main():
    token = getattr(config, "TOKEN", None)
    if not token:
        logger.error("❌ Токен не настроен! Проверьте .env")
        print("❌ Токен не настроен! Проверьте .env")
        return

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))
    app.add_handler(CallbackQueryHandler(handle_quality_choice, pattern="^quality_"))

    logger.info("✅ Бот запущен.")
    app.run_polling()


if __name__ == "__main__":
    main()
