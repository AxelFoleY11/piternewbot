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
    utils.track_user_activity(user.id, "start")
    
    if await utils.check_subscription(user.id, context):
        remaining = utils.get_remaining_downloads(user.id, config.MAX_DAILY_DOWNLOADS)
        await update.message.reply_text(
            f"👋 Привет! Отправь ссылку на видео.\n\n"
            f"📊 Осталось скачиваний: {remaining}/{config.MAX_DAILY_DOWNLOADS}"
        )
    else:
        await update.message.reply_text(
            "📢 Подпишись на каналы, чтобы использовать бота:",
            reply_markup=utils.subscription_keyboard()
        )


# --- /analytics ---
async def analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Проверяем права администратора
    if user.id != config.ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещен. Только администратор может просматривать аналитику.")
        return
    
    stats = utils.get_analytics_summary()
    
    # Формируем сообщение с аналитикой
    message = f"📊 **Аналитика бота**\n\n"
    message += f"👥 **Пользователи:**\n"
    message += f"• Всего пользователей: {stats['total_users']}\n"
    message += f"• Подписанных: {stats['subscribed_users']}\n"
    message += f"• Процент подписки: {stats['subscription_rate']}%\n"
    message += f"• Активных сегодня: {stats['active_users_today']}\n\n"
    
    message += f"📥 **Скачивания:**\n"
    message += f"• Сегодня: {stats['today_downloads']}\n"
    message += f"• Всего: {stats['total_downloads']}\n\n"
    
    # Показываем статистику за последние 7 дней
    daily_stats = stats['daily_stats']
    if daily_stats:
        message += f"📅 **За последние дни:**\n"
        sorted_days = sorted(daily_stats.items(), reverse=True)[:7]
        for date, count in sorted_days:
            message += f"• {date}: {count} скачиваний\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')


# --- /system ---
async def system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Проверяем права администратора
    if user.id != config.ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещен. Только администратор может просматривать системную информацию.")
        return
    
    load_info = utils.get_system_load()
    
    message = f"🖥️ **Состояние системы**\n\n"
    message += f"📊 **Нагрузка:**\n"
    message += f"• Активных скачиваний: {load_info['active_downloads']}/{load_info['max_concurrent']}\n"
    message += f"• Загрузка: {load_info['load_percentage']:.1f}%\n\n"
    
    message += f"⚙️ **Конфигурация:**\n"
    message += f"• Максимум одновременных скачиваний: {config.MAX_CONCURRENT_DOWNLOADS}\n"
    message += f"• Максимальный размер файла: {config.MAX_FILE_SIZE // (1024*1024)}MB\n"
    message += f"• Лимит скачиваний в день: {config.MAX_DAILY_DOWNLOADS}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')


# --- /userstats ---
async def userstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Проверяем права администратора
    if user.id != config.ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещен. Только администратор может просматривать статистику пользователей.")
        return
    
    # Получаем аргументы команды
    if not context.args:
        await update.message.reply_text("❌ Укажите ID пользователя: /userstats <user_id>")
        return
    
    try:
        target_user_id = int(context.args[0])
        user_stats = utils.get_user_stats(target_user_id)
        
        if not user_stats:
            await update.message.reply_text(f"❌ Пользователь {target_user_id} не найден в статистике.")
            return
        
        message = f"👤 **Статистика пользователя {target_user_id}:**\n\n"
        message += f"📅 Первый визит: {user_stats['first_seen']}\n"
        message += f"📅 Последний визит: {user_stats['last_seen']}\n"
        message += f"📥 Всего скачиваний: {user_stats['total_downloads']}\n"
        message += f"✅ Подписка: {'Да' if user_stats['is_subscribed'] else 'Нет'}\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID пользователя. Используйте числа.")


# --- /limits ---
async def limits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await utils.check_subscription(user.id, context):
        await update.message.reply_text(
            "❌ Сначала подпишись на каналы:",
            reply_markup=utils.subscription_keyboard()
        )
        return
    
    used = utils.get_user_download_count(user.id)
    remaining = utils.get_remaining_downloads(user.id, config.MAX_DAILY_DOWNLOADS)
    
    await update.message.reply_text(
        f"📊 Статистика скачиваний:\n\n"
        f"✅ Использовано: {used}/{config.MAX_DAILY_DOWNLOADS}\n"
        f"🔄 Осталось: {remaining}\n"
        f"⏰ Сброс: завтра в 00:00"
    )


# --- обработка ссылок ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    utils.track_user_activity(user.id, "message")
    
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

    # Проверяем лимиты скачиваний
    if not utils.can_user_download(user.id, config.MAX_DAILY_DOWNLOADS):
        await update.message.reply_text(
            f"❌ Достигнут дневной лимит скачиваний!\n\n"
            f"📊 Лимит: {config.MAX_DAILY_DOWNLOADS} скачиваний в день\n"
            f"🔄 Сброс: завтра в 00:00"
        )
        return
    
    kb, remaining = utils.quality_keyboard(norm, user.id)
    await update.message.reply_text(
        f"🎬 Выберите качество:\n\n"
        f"📊 Осталось скачиваний: {remaining}/{config.MAX_DAILY_DOWNLOADS}",
        reply_markup=kb
    )


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

    # Разбираем callback_data: quality_720_abc12345
    parts = data.split("_")
    if len(parts) != 3:
        await query.edit_message_text("⚠️ Ошибка: неверный формат данных")
        return
    
    quality = parts[1]
    video_id = parts[2]
    url = utils.pop_cached_url(video_id)

    if not url:
        await query.edit_message_text("⚠️ Ошибка: ссылка устарела")
        return

    if not await utils.check_subscription(query.from_user.id, context):
        await query.edit_message_text("❌ Подписка обязательна.")
        return

    # Проверяем лимиты скачиваний еще раз
    if not utils.can_user_download(query.from_user.id, config.MAX_DAILY_DOWNLOADS):
        await query.edit_message_text(
            f"❌ Достигнут дневной лимит скачиваний!\n\n"
            f"📊 Лимит: {config.MAX_DAILY_DOWNLOADS} скачиваний в день\n"
            f"🔄 Сброс: завтра в 00:00"
        )
        return

    try:
        await query.edit_message_text(f"⏳ Скачиваю в {quality}p...")
        file_path = utils.download_video(url, quality, query.from_user.id)
        
        # Увеличиваем счетчик скачиваний
        utils.increment_download_count(query.from_user.id)

        if not os.path.exists(file_path):
            await query.edit_message_text("❌ Ошибка: файл не был создан")
            return

        file_size = os.path.getsize(file_path)
        if file_size > config.TELEGRAM_LIMIT:
            await query.edit_message_text("⚠️ Файл слишком большой для Telegram (>2 ГБ)")
            try:
                os.remove(file_path)
            except Exception:
                pass
            return

        # Отправляем видео
        with open(file_path, "rb") as f:
            await query.message.reply_video(
                video=f,
                caption=f"📹 Видео в качестве {quality}p"
            )

        # Получаем оставшиеся скачивания
        remaining = utils.get_remaining_downloads(query.from_user.id, config.MAX_DAILY_DOWNLOADS)
        await query.edit_message_text(f"✅ Видео отправлено!\n\n📊 Осталось скачиваний: {remaining}/{config.MAX_DAILY_DOWNLOADS}")

        # Удаляем временный файл
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"Не удалось удалить файл {file_path}: {e}")
            
    except Exception as e:
        logger.error(f"Ошибка скачивания: {e}")
        await query.edit_message_text(f"❌ Ошибка скачивания: {str(e)}")


def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("limits", limits))
    app.add_handler(CommandHandler("analytics", analytics))
    app.add_handler(CommandHandler("system", system))
    app.add_handler(CommandHandler("userstats", userstats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button))
    print("✅ Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
