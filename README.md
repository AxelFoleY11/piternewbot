[Uploading README.md…]()
# piternewbot

Telegram бот для скачивания видео (YouTube, TikTok, Instagram, VK, Vimeo, Dailymotion).

## Возможности
- Проверка подписки на каналы перед скачиванием
- Качество до 1080p
- Поддержка коротких ссылок (shorts, youtu.be, embed, insta, tiktok short)
- Очистка временных файлов

## Установка
```bash
git clone https://github.com/yourname/piternewbot.git
cd piternewbot
pip install -r requirements.txt
cp .env.example .env   # вписать токен и admin_id
python bot.py
