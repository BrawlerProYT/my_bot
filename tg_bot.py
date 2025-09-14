import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import yt_dlp
import os

# === Настройки ===
TELEGRAM_BOT_TOKEN = "7746230370:AAGqP9HCv4thXXnHv67rVd8iB75rTMWn8H0"
DEVELOPER_ID = 8213990877  # 👉 сюда вставь свой Telegram ID

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("TG-Music-Bot")

# Храним результаты поиска для каждого пользователя
user_search_results = {}
# Храним ID всех пользователей и чатов
active_chats = set()


# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    active_chats.add(chat_id)  # добавляем чат в список активных

    await update.message.reply_text(
        "🎵 Добро пожаловать в *TG Musik Bot*! 🎵\n\n"
        "Отправь название песни или исполнителя, и я найду её на YouTube 🔎",
        parse_mode="Markdown",
    )


# === Обработка текста (поиск) ===
async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.effective_chat.id
    text = update.message.text

    # логируем
    logger.info(f"[{chat_id}] {update.message.from_user.username or user_id}: {text}")
    active_chats.add(chat_id)

    # если пишет разработчик — делаем рассылку
    if user_id == DEVELOPER_ID:
        await broadcast_message(context, f"📢 Сообщение от разработчика:\n\n{text}")
        return

    await update.message.reply_text(f"🔎 Ищу *{text}* ...", parse_mode="Markdown")

    try:
        # ⚡ быстрый поиск (5 треков)
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "default_search": "ytsearch5",
            "extract_flat": True,  # только метаданные, без загрузки форматов
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(text, download=False)

        results = []
        for entry in info.get("entries", []):
            results.append(
                {
                    "title": entry.get("title"),
                    "id": entry.get("id"),
                    "url": f"https://www.youtube.com/watch?v={entry['id']}",
                }
            )

        if not results:
            await update.message.reply_text("⚠️ Ничего не найдено.")
            return

        # сохраняем для пользователя
        user_search_results[user_id] = results

        # показываем список (5 кнопок)
        keyboard = []
        for i, track in enumerate(results[:5]):
            keyboard.append(
                [
                    InlineKeyboardButton(
                        track["title"][:40], callback_data=f"choose_{i}"
                    )
                ]
            )

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🎶 Вот что я нашёл:\nВыбери трек 👇", reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(e)
        await update.message.reply_text("❌ Ошибка при поиске.")


# === Отправка выбранного результата с кнопками ===
async def send_result(update, context, user_id, index):
    results = user_search_results.get(user_id, [])
    if not results or index >= len(results):
        await context.bot.send_message(user_id, "⚠️ Больше результатов нет.")
        return

    track = results[index]
    keyboard = [
        [InlineKeyboardButton("⬇️ Скачать", callback_data=f"download_{index}")],
        [InlineKeyboardButton("➡️ Дальше", callback_data=f"next_{index+1}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if isinstance(update, Update):
        chat_id = update.effective_chat.id
    else:
        chat_id = update.message.chat_id if update.message else user_id

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"*{track['title']}*\n{track['url']}",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


# === Обработка кнопок ===
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # выбор из списка
    if data.startswith("choose_"):
        index = int(data.split("_")[1])
        await send_result(query, context, user_id, index)

    # скачать
    elif data.startswith("download_"):
        index = int(data.split("_")[1])
        await download_audio(query, context, user_id, index)

    # следующий результат
    elif data.startswith("next_"):
        index = int(data.split("_")[1])
        await send_result(query, context, user_id, index)


# === Скачивание трека ===
async def download_audio(query, context, user_id, index):
    results = user_search_results.get(user_id, [])
    if not results or index >= len(results):
        await context.bot.send_message(user_id, "⚠️ Ошибка: трек не найден.")
        return

    track = results[index]
    url = track["url"]

    await query.edit_message_text(
        f"⬇️ Скачиваю: *{track['title']}* ...", parse_mode="Markdown"
    )

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{user_id}_%(id)s.%(ext)s",
        "quiet": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_name = f"{user_id}_{info['id']}.mp3"

        await context.bot.send_audio(
            chat_id=user_id, audio=open(file_name, "rb"), title=track["title"]
        )
        os.remove(file_name)

    except Exception as e:
        logger.error(e)
        await context.bot.send_message(user_id, "❌ Ошибка при скачивании.")


# === Рассылка от разработчика ===
async def broadcast_message(context, text: str):
    for chat_id in list(active_chats):
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            logger.error(f"Ошибка рассылки в чат {chat_id}: {e}")
            active_chats.discard(chat_id)


# === Запуск бота ===
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query))
    application.add_handler(CallbackQueryHandler(button_callback))

    logger.info("TG Musik Bot запущен!")
    application.run_polling()


if __name__ == "__main__":
    main()
