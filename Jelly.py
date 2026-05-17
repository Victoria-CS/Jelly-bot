import json, time
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

TOKEN = os.getenv("BOT_TOKEN")
MANAGER_CHAT_ID = -4790241047

RATE_LIMIT_MESSAGES = 5
RATE_LIMIT_SECONDS = 10
BAN_DURATION_SECONDS = 60 * 60 

active_chats = set()
message_timestamps = {}
banned_users = {}

BANNED_FILE = "banned.json"
SPAM_LOG = "spam_log.txt"


def save_bans():
    with open(BANNED_FILE, "w", encoding="utf-8") as f:
        json.dump(banned_users, f, ensure_ascii=False, indent=2)

def log_spam(user_id, reason):
    with open(SPAM_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{time.ctime()}] User {user_id}: {reason}\n")

def is_banned(user_id):
    if str(user_id) in banned_users:
        if time.time() < banned_users[str(user_id)]:
            return True
        else:
            del banned_users[str(user_id)]
            save_bans()
    return False

def check_rate_limit(user_id):
    now = time.time()
    timestamps = message_timestamps.get(user_id, [])
    timestamps = [t for t in timestamps if now - t < RATE_LIMIT_SECONDS]
    timestamps.append(now)
    message_timestamps[user_id] = timestamps
    return len(timestamps) > RATE_LIMIT_MESSAGES

app = ApplicationBuilder().token(TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inline_keyboard = [
        [
            InlineKeyboardButton("📷 Instagram", url="https://www.instagram.com/jelly.azerbaijan/"),
            InlineKeyboardButton("🎵 TikTok", url="https://www.tiktok.com/@jelly.azerbaijan")
        ],
        [
            InlineKeyboardButton("🧵 Threads", url="https://www.threads.net/@jelly.azerbaijan"),
            InlineKeyboardButton("🍬 Каталог", url="https://jellycatalog.com")
        ]
    ]

    reply_keyboard = [[KeyboardButton("💬 Связаться с менеджером")]]

    text = (
        "🍭 Добро пожаловать в *Jelly!* 🍭\n\n"
        "Следи за нами в соцсетях и узнавай о новинках первыми 💖"
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard)
    )

    await update.message.reply_text(
        "👇 Выбери, что хочешь сделать:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    )


async def client_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    if update.message.text == "💬 Связаться с менеджером":
        if user.id in active_chats:
            await update.message.reply_text("Ты уже общаешься с менеджером 💬")
            return

        active_chats.add(user.id)
        await update.message.reply_text(
            "💬 Напиши свой вопрос, и менеджер скоро ответит!\n"
            "Если захочешь закончить диалог — нажми кнопку ниже 👇",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Завершить диалог", callback_data=f"end_chat:{user.id}")]
            ])
        )


async def client_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    text = update.message.text or "(без текста)"

    if is_banned(user_id):
        await update.message.reply_text("🚫 Ты временно заблокирован за спам. Попробуй позже 💖")
        return

    if check_rate_limit(user_id):
        log_spam(user_id, "Слишком частые сообщения")
        await update.message.reply_text("⚠️ Ты пишешь слишком часто! Подожди немного 💬")
        if len(message_timestamps[user_id]) > RATE_LIMIT_MESSAGES * 2:
            banned_users[str(user_id)] = time.time() + BAN_DURATION_SECONDS
            save_bans()
            log_spam(user_id, "Временная блокировка за спам")
            await update.message.reply_text("🚫 Ты временно заблокирован за спам (1 час).")
        return

    if user_id not in active_chats:
        active_chats.add(user_id)

    msg = f"💬 Сообщение от @{user.username or user.first_name} (ID {user_id}):\n{text}"
    keyboard = [[InlineKeyboardButton("✅ Завершить диалог", callback_data=f"end_chat:{user_id}")]]
    await context.bot.send_message(chat_id=MANAGER_CHAT_ID, text=msg, reply_markup=InlineKeyboardMarkup(keyboard))
    await update.message.reply_text("Спасибо! Менеджер скоро ответит 🩵")


async def manager_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message and "ID" in update.message.reply_to_message.text:
        try:
            reply_text = update.message.text
            original_text = update.message.reply_to_message.text
            user_id = int(original_text.split("ID ")[1].split(")")[0])
            await context.bot.send_message(chat_id=user_id, text=f"💌 Ответ от менеджера Jelly 🍬:\n{reply_text}")
        except Exception as e:
            await update.message.reply_text(f"Ошибка при отправке ответа: {e}")


async def end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split(":")
    user_id = int(data[1])

    if user_id in active_chats:
        active_chats.remove(user_id)

    try:
        await context.bot.send_message(chat_id=user_id, text="Диалог завершён 💖")
        await send_rating_request(context, user_id)
    except:
        pass

async def send_rating_request(context, user_id):
    keyboard = [[
        InlineKeyboardButton("⭐", callback_data=f"rate:1:{user_id}"),
        InlineKeyboardButton("⭐⭐", callback_data=f"rate:2:{user_id}"),
        InlineKeyboardButton("⭐⭐⭐", callback_data=f"rate:3:{user_id}"),
        InlineKeyboardButton("⭐⭐⭐⭐", callback_data=f"rate:4:{user_id}"),
        InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data=f"rate:5:{user_id}")
    ]]
    await context.bot.send_message(chat_id=user_id, text="⭐ Оцени общение с менеджером:", reply_markup=InlineKeyboardMarkup(keyboard))


async def rating_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split(":")
    rating = int(data[1])
    user_id = int(data[2])

    await query.message.reply_text("Спасибо за твою оценку 💖")
    await context.bot.send_message(chat_id=MANAGER_CHAT_ID, text=f"⭐ Пользователь (ID {user_id}) поставил оценку: {rating}⭐")


app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE & filters.Regex("^💬 Связаться с менеджером$"), client_menu_button))
app.add_handler(CallbackQueryHandler(end_chat, pattern="^end_chat:"))
app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT, client_message))
app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.REPLY & filters.TEXT, manager_reply))
app.add_handler(CallbackQueryHandler(rating_callback, pattern="^rate:"))

app.run_polling(close_loop=False)
