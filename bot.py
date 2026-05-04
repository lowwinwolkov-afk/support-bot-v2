import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from datetime import datetime

TOKEN = "8288994829:AAHh5SqqJyWe_3gskGRz10sv5vLyw9ryBf0"
SUPPORT_CHAT_ID = 5530223549

conn = sqlite3.connect("tickets.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    message TEXT,
    status TEXT,
    history TEXT,
    created_at TEXT
)
""")
conn.commit()

def create_ticket(user_id, username, message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO tickets (user_id, username, message, status, history, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, username, message, "NEW", message, now)
    )
    conn.commit()
    return cursor.lastrowid

def update_ticket(ticket_id, status=None, reply=None):
    cursor.execute("SELECT history FROM tickets WHERE ticket_id=?", (ticket_id,))
    history = cursor.fetchone()[0]
    if reply:
        history += f"\nSUPPORT: {reply}"
    if status:
        cursor.execute("UPDATE tickets SET status=?, history=? WHERE ticket_id=?", (status, history, ticket_id))
    else:
        cursor.execute("UPDATE tickets SET history=? WHERE ticket_id=?", (history, ticket_id))
    conn.commit()

def buttons(ticket_id):
    keyboard = [
        [InlineKeyboardButton("Ответить", callback_data=f"reply_{ticket_id}")],
        [InlineKeyboardButton("В ожидании", callback_data=f"waiting_{ticket_id}")],
        [InlineKeyboardButton("Закрыть", callback_data=f"close_{ticket_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Напишите сообщение в поддержку.")

async def user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    text = update.message.text
    ticket_id = create_ticket(user.id, user.first_name, text)

    await context.bot.send_message(
        chat_id=SUPPORT_CHAT_ID,
        text=f"Тикет #{ticket_id}\nОт: {user.first_name}\n{text}",
        reply_markup=buttons(ticket_id)
    )

    await update.message.reply_text("Сообщение отправлено!")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, ticket_id = query.data.split("_")
    ticket_id = int(ticket_id)

    if action == "reply":
        context.user_data["ticket"] = ticket_id
        await query.message.reply_text("Напишите ответ пользователю:")

    elif action == "waiting":
        update_ticket(ticket_id, status="WAITING")
        await query.message.reply_text("Тикет в ожидании")

    elif action == "close":
        update_ticket(ticket_id, status="CLOSED")
        await query.message.reply_text("Тикет закрыт")

async def support_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "ticket" in context.user_data:
        ticket_id = context.user_data["ticket"]
        text = update.message.text

        cursor.execute("SELECT user_id FROM tickets WHERE ticket_id=?", (ticket_id,))
        user_id = cursor.fetchone()[0]

        await context.bot.send_message(user_id, f"Саппорт: {text}")
        update_ticket(ticket_id, reply=text)

        await update.message.reply_text("Ответ отправлен!")
        del context.user_data["ticket"]

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.User(SUPPORT_CHAT_ID), user_message))
app.add_handler(MessageHandler(filters.TEXT & filters.User(SUPPORT_CHAT_ID), support_reply))
app.add_handler(CallbackQueryHandler(button))

app.run_polling()