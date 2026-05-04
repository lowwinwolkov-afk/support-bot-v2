import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

TOKEN = "8288994829:AAHh5SqqJyWe_3gskGRz10sv5vLyw9ryBf0"
SUPPORT_CHAT_ID = -1003953681428  # группа саппорта

# ---------------- DATABASE ----------------
conn = sqlite3.connect("tickets.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    message TEXT,
    status TEXT,
    history TEXT,
    created_at TEXT,
    assigned_to INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER,
    action TEXT,
    actor_id INTEGER,
    created_at TEXT
)
""")

conn.commit()


# ---------------- HELPERS ----------------
def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(ticket_id, action, actor_id):
    cursor.execute(
        "INSERT INTO logs (ticket_id, action, actor_id, created_at) VALUES (?, ?, ?, ?)",
        (ticket_id, action, actor_id, now())
    )
    conn.commit()


def create_ticket(user_id, username, message):
    cursor.execute(
        "INSERT INTO tickets (user_id, username, message, status, history, created_at, assigned_to) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, username, message, "NEW", message, now(), None)
    )
    conn.commit()
    return cursor.lastrowid


def update_status(ticket_id, status):
    cursor.execute("UPDATE tickets SET status=? WHERE id=?", (status, ticket_id))
    conn.commit()


def get_ticket(ticket_id):
    cursor.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,))
    return cursor.fetchone()


def update_history(ticket_id, text):
    cursor.execute("SELECT history FROM tickets WHERE id=?", (ticket_id,))
    h = cursor.fetchone()[0] or ""
    h += f"\nSUPPORT: {text}"
    cursor.execute("UPDATE tickets SET history=? WHERE id=?", (h, ticket_id))
    conn.commit()


# ---------------- UI ----------------
def buttons(ticket_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✋ Взять", callback_data=f"claim_{ticket_id}")],
        [InlineKeyboardButton("💬 Ответить", callback_data=f"reply_{ticket_id}")],
        [InlineKeyboardButton("⏳ В ожидании", callback_data=f"wait_{ticket_id}")],
        [InlineKeyboardButton("❌ Закрыть", callback_data=f"close_{ticket_id}")]
    ])


# ---------------- COMMANDS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📩 Напишите сообщение в поддержку")


# ---------------- USER MESSAGE ----------------
async def user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    ticket_id = create_ticket(user.id, user.first_name, update.message.text)
    log(ticket_id, "CREATED", user.id)

    await context.bot.send_message(
        chat_id=SUPPORT_CHAT_ID,
        text=f"🎫 Тикет #{ticket_id}\n👤 {user.first_name}\n\n{update.message.text}",
        reply_markup=buttons(ticket_id)
    )

    await update.message.reply_text("✅ Ваше обращение отправлено")


# ---------------- CALLBACK ----------------
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        action, ticket_id = query.data.split("_")
        ticket_id = int(ticket_id)
    except:
        return

    ticket = get_ticket(ticket_id)
    if not ticket:
        await query.message.reply_text("❌ Тикет не найден")
        return

    user_id = ticket[1]
    assigned = ticket[7]

    # ---------------- CLAIM ----------------
    if action == "claim":
        if assigned:
            await query.message.reply_text("❌ Уже взят")
            return

        cursor.execute(
            "UPDATE tickets SET assigned_to=? WHERE id=?",
            (query.from_user.id, ticket_id)
        )
        conn.commit()

        log(ticket_id, "CLAIMED", query.from_user.id)

        await query.message.reply_text("✔ Вы взяли тикет")
        return

    # ---------------- WAIT ----------------
    if action == "wait":
        update_status(ticket_id, "WAITING")
        log(ticket_id, "WAITING", query.from_user.id)

        await context.bot.send_message(
            chat_id=user_id,
            text="⏳ Ваш тикет в ожидании ответа"
        )

        await query.message.reply_text("⏳ Отправлено")
        return

    # ---------------- CLOSE ----------------
    if action == "close":
        update_status(ticket_id, "CLOSED")
        log(ticket_id, "CLOSED", query.from_user.id)

        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Тикет закрыт"
        )

        await query.message.reply_text("❌ Закрыто")
        return

    # ---------------- REPLY ----------------
    if action == "reply":
        if assigned and assigned != query.from_user.id:
            await query.message.reply_text("❌ Это не ваш тикет")
            return

        context.user_data["reply_ticket"] = ticket_id
        await query.message.reply_text("✍️ Напишите ответ пользователю")


# ---------------- SUPPORT REPLY ----------------
async def support_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "reply_ticket" not in context.user_data:
        return

    ticket_id = context.user_data["reply_ticket"]
    text = update.message.text
    admin_id = update.message.from_user.id

    # получаем тикет
    cursor.execute("SELECT user_id FROM tickets WHERE id=?", (ticket_id,))
    result = cursor.fetchone()

    if not result:
        await update.message.reply_text("❌ Тикет не найден")
        return

    user_id = result[0]

    # отправка пользователю
    await context.bot.send_message(
        chat_id=user_id,
        text=f"📩 Ответ поддержки:\n\n{text}"
    )

    # сохраняем историю
    cursor.execute("SELECT history FROM tickets WHERE id=?", (ticket_id,))
    history = cursor.fetchone()[0] or ""
    history += f"\nSUPPORT: {text}"

    cursor.execute(
        "UPDATE tickets SET history=? WHERE id=?",
        (history, ticket_id)
    )
    conn.commit()

    # лог
    cursor.execute(
        "INSERT INTO logs (ticket_id, action, actor_id, created_at) VALUES (?, ?, ?, ?)",
        (ticket_id, "REPLY", admin_id, now())
    )
    conn.commit()

    await update.message.reply_text("✅ Отправлено пользователю")

    del context.user_data["reply_ticket"]


# ---------------- APP ----------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_message))
app.add_handler(MessageHandler(filters.TEXT & filters.User(SUPPORT_CHAT_ID), support_reply))
app.add_handler(CallbackQueryHandler(callback))

app.run_polling()
