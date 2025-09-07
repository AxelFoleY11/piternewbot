from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    CallbackContext
)
import config
import utils
import os
import re
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Проверка URL
def is_valid_url(url: str) -> bool:
    patterns = [
        r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+',
        r'(https?://)?(www\.)?tiktok\.com/.+',
        r'(https?://)?(www\.)?instagram\.com/.+',
        r'(https?://)?(www\.)?vk\.com/.+',
        r'(https?://)?(www\.)?dailymotion\.com/.+',
        r'(https?://)?(www\.)?vimeo\.com/.+'
    ]
    return any(re.match(pattern, url) for pattern in patterns)

# Команда /start
async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    if await utils.check_subscription(user.id, context):
        await update.message.reply_text(
            "🎬 <b>Добро пожаловать в видео-бот!</b>\n\n"
            "Отправьте ссылку на видео с одной из поддерживаемых платформ:\n"
            "YouTube, TikTok, Instagram, VK, Dailymotion, Vimeo",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "📢 <b>Для использования бота подпишитесь на наши каналы:</b>",
            reply_markup=utils.subscription_keyboard(),
            parse_mode="HTML"
        )

# Проверка подписки
async def check_subscription_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if await utils.check_subscription(query.from_user.id, context):
        await query.edit_message_text(
            "✅ <b>Подписка подтверждена!</b>\n\n"
            "Отправьте ссылку на видео:",
            parse_mode="HTML"
        )
    else:
        await query.answer("❌ Вы подписаны не на все каналы!", show_alert=True)

# Обработка текстовых сообщений
async def handle_message(update: Update, context: CallbackContext):
    user = update.effective_user
    text = update.message.text
    
    if not await utils.check_subscription(user.id, context):
        await update.message.reply_text(
            "❌ <b>Доступ запрещен!</b>\n\n"
            "Подпишитесь на все каналы для использования бота:",
            reply_markup=utils.subscription_keyboard(),
            parse_mode="HTML"
        )
        return
    
    if is_valid_url(text):
        await update.message.reply_text(
            "🎬 <b>Выберите качество видео:</b>",
            reply_markup=utils.quality_keyboard(text),
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "⚠️ <b>Неверная ссылка!</b>\n\n"
            "Поддерживаемые платформы:\n"
            "YouTube, TikTok, Instagram, VK, Dailymotion, Vimeo",
            parse_mode="HTML"
        )

# Обработка выбора качества
async def handle_quality_choice(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")
    quality = data[1]
    url = "_".join(data[2:])
    
    if not await utils.check_subscription(query.from_user.id, context):
        await query.answer("❌ Вы отписались от каналов!", show_alert=True)
        return
    
    await query.answer("⏳ Начинаю загрузку...")
    await query.edit_message_text(f"🔄 <b>Скачиваю видео в {quality}p...</b>", parse_mode="HTML")
    
    try:
        os.makedirs("downloads", exist_ok=True)
        
        file_path = utils.download_video(url, quality)
        
        if os.path.getsize(file_path) > config.MAX_FILE_SIZE:
            os.remove(file_path)
            raise ValueError("Файл превышает 50MB")
        
        await context.bot.send_video(
            chat_id=query.message.chat_id,
            video=open(file_path, "rb"),
            caption=f"✅ Видео {quality}p успешно скачано!",
            supports_streaming=True
        )
        os.remove(file_path)
        
    except Exception as e:
        error_msg = f"❌ Ошибка: {str(e)}"
        await query.edit_message_text(error_msg)
        logger.error(f"Error downloading video: {e}")
        
        try:
            await context.bot.send_message(
                config.ADMIN_ID,
                f"Ошибка у @{query.from_user.username}:\n{error_msg}\n\nURL: {url}"
            )
        except:
            pass

# Основная функция
def main():
    app = Application.builder().token(config.TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))
    app.add_handler(CallbackQueryHandler(handle_quality_choice, pattern="^quality_"))
    
    logger.info("Бот запущен...")
    print("Бот запущен! Нажмите Ctrl+C для остановки.")
    app.run_polling()

if __name__ == "__main__":
    main()
