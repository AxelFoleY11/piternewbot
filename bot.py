
# -*- coding: utf-8 -*-
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

def is_valid_url(url: str) -> bool:
    """Проверяет валидность URL"""
    patterns = [
        # YouTube
        r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/(watch\?v=|embed/|v/|.+?v=)([a-zA-Z0-9_-]{11})',
        # TikTok конкретные видео
        r'(https?://)?(www\.|m\.|vm\.)?tiktok\.com/.+?/video/\d+',
        r'(https?://)?(www\.|m\.|vm\.)?tiktok\.com/.+?/v/\d+',
        r'(https?://)?(vm\.|m\.)?tiktok\.com/\w+/',
        # Instagram
        r'(https?://)?(www\.)?instagram\.com/(p|reel)/([a-zA-Z0-9_-]+)/',
        # Другие платформы
        r'(https?://)?(www\.)?vk\.com/video(-?\d+_\d+)',
        r'(https?://)?(www\.)?dailymotion\.com/video/([a-zA-Z0-9]+)',
        r'(https?://)?(www\.)?vimeo\.com/([0-9]+)'
    ]
    
    # Проверяем что это не главная страница
    if any(url.startswith(base) for base in [
        'https://www.tiktok.com/',
        'https://tiktok.com/',
        'https://www.instagram.com/',
        'https://instagram.com/',
        'https://www.youtube.com/',
        'https://youtube.com/'
    ]) and '/video/' not in url and '/watch?' not in url and '/p/' not in url:
        return False
    
    return any(re.match(pattern, url) for pattern in patterns)

async def start(update: Update, context: CallbackContext):
    """Обработчик команды /start"""
    user = update.effective_user
    logger.info(f"Получена команда /start от {user.id}")
    
    if await utils.check_subscription(user.id, context):
        await update.message.reply_text(
            "🎬 <b>Добро пожаловать в видео-бот!</b>\n\n"
            "Отправьте ссылку на видео с одной из поддерживаемых платформ:\n"
            "YouTube, TikTok, Instagram, VK, Dailymotion, Vimeo\n\n"
            "<b>Примеры рабочих ссылок:</b>\n"
            "• YouTube: https://youtube.com/watch?v=...\n"
            "• TikTok: https://tiktok.com/@user/video/123...\n"
            "• Instagram: https://instagram.com/p/...",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "📢 <b>Для использования бота подпишитесь на наши каналы:</b>",
            reply_markup=utils.subscription_keyboard(),
            parse_mode="HTML"
        )

async def check_subscription_callback(update: Update, context: CallbackContext):
    """Обработчик проверки подписки"""
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

async def handle_message(update: Update, context: CallbackContext):
    """Обработчик текстовых сообщений"""
    user = update.effective_user
    text = update.message.text.strip()
    
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
            "<b>Поддерживаемые форматы:</b>\n"
            "• YouTube: https://youtube.com/watch?v=...\n"
            "• TikTok: https://tiktok.com/@user/video/123...\n"
            "• Instagram: https://instagram.com/p/...\n\n"
            "<b>Не принимаются:</b> главные страницы, профили, поиск",
            parse_mode="HTML"
        )

async def handle_quality_choice(update: Update, context: CallbackContext):
    """Обработчик выбора качества"""
    query = update.callback_query
    data = query.data.split("_")
    quality = data[1]
    url = "_".join(data[2:])
    
    # Повторная проверка подписки
    if not await utils.check_subscription(query.from_user.id, context):
        await query.answer("❌ Вы отписались от каналов!", show_alert=True)
        return
    
    await query.answer("⏳ Начинаю загрузку...")
    await query.edit_message_text(f"🔄 <b>Скачиваю видео в {quality}p...</b>", parse_mode="HTML")
    
    try:
        # Создаем папку downloads если её нет
        os.makedirs("downloads", exist_ok=True)
        
        file_path = utils.download_video(url, quality)
        
        if os.path.getsize(file_path) > config.MAX_FILE_SIZE:
            os.remove(file_path)
            raise ValueError("Файл превышает 50MB")
        
        await context.bot.send_video(
            chat_id=query.message.chat_id,
            video=open(file_path, "rb"),
            caption=f"✅ Видео {quality}p успешно скачано!",
            supports_streaming=True,
            read_timeout=60,
            write_timeout=60,
            connect_timeout=60
        )
        os.remove(file_path)
        
    except Exception as e:
        error_msg = f"❌ Ошибка: {str(e)}"
        await query.edit_message_text(error_msg)
        logger.error(f"Error downloading video: {e}")
        
        # Отправка ошибки админу
        try:
            await context.bot.send_message(
                config.ADMIN_ID,
                f"Ошибка у @{query.from_user.username}:\n{error_msg}\n\nURL: {url}"
            )
        except:
            pass

def main():
    """Основная функция"""
    try:
        # Проверка токена
        if not config.TOKEN or config.TOKEN == "your_bot_token_here":
            logger.error("❌ Токен не настроен! Проверьте файл .env")
            return
        
        logger.info(f"✅ Токен получен: {config.TOKEN[:10]}...")
        
        # Создаем приложение с увеличенными таймаутами
        app = Application.builder()\
            .token(config.TOKEN)\
            .read_timeout(30)\
            .connect_timeout(30)\
            .pool_timeout(30)\
            .build()
        
        # Добавляем обработчики
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))
        app.add_handler(CallbackQueryHandler(handle_quality_choice, pattern="^quality_"))
        
        logger.info("✅ Бот запущен! Нажмите Ctrl+C для остановки.")
        print("✅ Бот запущен! Проверьте Telegram.")
        
        app.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска: {e}")
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
