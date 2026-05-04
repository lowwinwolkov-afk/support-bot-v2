import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = "8288994829:AAHh5SqqJyWe_3gskGRz10sv5vLyw9ryBf0"
SUPPORT_CHAT_ID = -1003953681428

# --- DB ---
conn = sqlite3.connect("tickets.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    message TEXT,
    status TEXT,
    created_at TEXT
)
""")
conn.commit()


def create_ticket(user_id, username, message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO tickets (user_id, username, message, status, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, message, "NEW", now)
    )
    conn.commit()
    return cursor.lastrowid


def update_status(ticket_id, status):
    cursor.execute("UPDATE tickets SET status=? WHERE id=?", (status, ticket_id))
    conn.commit()


def get_user(ticket_id):
    cursor.execute("SELECT user_id FROM tickets WHERE id=?", (ticket_id,))
    return cursor.fetchone()


def panel(ticket_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Ответить", callback_data=f"reply_{ticket_id}")],
        [InlineKeyboardButton("⏳ В ожидании", callback_data=f"wait_{ticket_id}")],
        [InlineKeyboardButton("❌ Закрыть", callback_data=f"close_{ticket_id}")]
    ])


# --- START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Напиши сообщение в поддержку 👇")


# --- ALL MESSAGES ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    text = update.message.text

    # если это саппорт — игнорим
    if update.message.chat_id == SUPPORT_CHAT_ID:
        return

    ticket_id = create_ticket(user.id, user.first_name, text)

    await context.bot.send_message(
        chat_id=SUPPORT_CHAT_ID,
        text=f"🎫 Тикет #{ticket_id}\n👤 {user.first_name}\n\n{text}",
        reply_markup=panel(ticket_id)
    )

    await update.message.reply_text("✅ Ваше обращение отправлено!")


# --- BUTTONS ---
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, ticket_id = query.data.split("_")
    ticket_id = int(ticket_id)

    if action == "wait":
        update_status(ticket_id, "WAITING")
        await query.message.reply_text("⏳ В ожидании")

    elif action == "close":
        update_status(ticket_id, "CLOSED")
        await query.message.reply_text("❌ Закрыто")

    elif action == "reply":
        context.user_data["reply_ticket"] = ticket_id
        await query.message.reply_text("✍️ Напишите ответ пользователю:")


# --- SUPPORT REPLY ---
async def support_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "reply_ticket" not in context.user_data:
        return

    ticket_id = context.user_data["reply_ticket"]
    text = update.message.text

    user_data = get_user(ticket_id)
    if not user_data:
        return

    user_id = user_data[0]

    await context.bot.send_message(
        chat_id=user_id,
        text=f"📩 Ответ от поддержки:\n\n{text}"
    )

    await update.message.reply_text("✅ Ответ отправлен!")
    del context.user_data["reply_ticket"]


# --- APP ---
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(MessageHandler(filters.TEXT & filters.COMMAND, support_reply))
app.add_handler(CallbackQueryHandler(buttons))

app.run_polling()