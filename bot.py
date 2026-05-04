import sqlite3
from datetime import datetime, timedelta
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
SUPPORT_CHAT_ID = -1003953681428

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
    assigned_to INTEGER,
    support_msg_id INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    muted_until TEXT,
    banned_until TEXT,
    last_ticket_time TEXT
)
""")

conn.commit()

# ---------------- HELPERS ----------------
def now():
    return datetime.now()

def now_str():
    return now().strftime("%Y-%m-%d %H:%M:%S")

def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def update_user(user_id, muted=None, banned=None, last_ticket=None):
    cursor.execute("""
    INSERT INTO users (user_id, muted_until, banned_until, last_ticket_time)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
    muted_until=COALESCE(?, muted_until),
    banned_until=COALESCE(?, banned_until),
    last_ticket_time=COALESCE(?, last_ticket_time)
    """, (user_id, muted, banned, last_ticket,
          muted, banned, last_ticket))
    conn.commit()

def get_ticket_by_message(msg_id):
    cursor.execute("SELECT * FROM tickets WHERE support_msg_id=?", (msg_id,))
    return cursor.fetchone()

# ---------------- UI ----------------
def buttons(ticket_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏳ В ожидании", callback_data=f"wait_{ticket_id}")],
        [InlineKeyboardButton("❌ Закрыть", callback_data=f"close_{ticket_id}")]
    ])

# ---------------- COMMAND ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📩 Напишите сообщение в поддержку")

# ---------------- USER MESSAGE ----------------
async def user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    data = get_user(user.id)

    # бан
    if data and data[2]:
        if datetime.strptime(data[2], "%Y-%m-%d %H:%M:%S") > now():
            return

    # мут
    if data and data[1]:
        if datetime.strptime(data[1], "%Y-%m-%d %H:%M:%S") > now():
            await update.message.reply_text("🔇 Вы временно ограничены")
            return

    # антиспам
    if data and data[3]:
        last = datetime.strptime(data[3], "%Y-%m-%d %H:%M:%S")
        if now() - last < timedelta(minutes=3):
            await update.message.reply_text("⏳ Подождите перед новым обращением")
            return

    update_user(user.id, last_ticket=now_str())

    cursor.execute("""
    INSERT INTO tickets (user_id, username, message, status, history, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user.id, user.first_name, update.message.text, "NEW", update.message.text, now_str()))
    conn.commit()

    ticket_id = cursor.lastrowid

    msg = await context.bot.send_message(
        chat_id=SUPPORT_CHAT_ID,
        text=f"🎫 Тикет #{ticket_id}\n👤 {user.first_name}\n\n{update.message.text}",
        reply_markup=buttons(ticket_id)
    )

    cursor.execute("UPDATE tickets SET support_msg_id=? WHERE id=?",
                   (msg.message_id, ticket_id))
    conn.commit()

    await update.message.reply_text("✅ Обращение отправлено")

# ---------------- CALLBACK ----------------
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, ticket_id = query.data.split("_")
    ticket_id = int(ticket_id)

    cursor.execute("SELECT user_id FROM tickets WHERE id=?", (ticket_id,))
    user_id = cursor.fetchone()[0]

    if action == "wait":
        await context.bot.send_message(user_id, f"⏳ Тикет #{ticket_id} в ожидании")

    elif action == "close":
        await context.bot.send_message(user_id, f"❌ Тикет #{ticket_id} закрыт")

# ---------------- SUPPORT REPLY ----------------
async def support_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != SUPPORT_CHAT_ID:
        return

    if not update.message.reply_to_message:
        return

    msg_id = update.message.reply_to_message.message_id
    ticket = get_ticket_by_message(msg_id)

    if not ticket:
        return

    ticket_id = ticket[0]
    user_id = ticket[1]
    assigned = ticket[7]

    support_id = update.message.from_user.id
    support_name = update.message.from_user.first_name

    # закрепление
    if assigned and assigned != support_id:
        await update.message.reply_text("❌ Тикет уже закреплён за другим саппортом")
        return

    if not assigned:
        cursor.execute(
            "UPDATE tickets SET assigned_to=? WHERE id=?",
            (support_id, ticket_id)
        )
        conn.commit()

    text = update.message.text

    # отправка пользователю
    await context.bot.send_message(
        chat_id=user_id,
        text=f"📩 Тикет #{ticket_id}\n👨‍💻 {support_name}:\n\n{text}"
    )

    # история
    cursor.execute("SELECT history FROM tickets WHERE id=?", (ticket_id,))
    history = cursor.fetchone()[0] or ""
    history += f"\n{support_name}: {text}"

    cursor.execute("UPDATE tickets SET history=? WHERE id=?",
                   (history, ticket_id))
    conn.commit()

    await update.message.reply_text(f"✅ Ответ отправлен (Тикет #{ticket_id})")

# ---------------- APP ----------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))

# ЛС
app.add_handler(MessageHandler(
    filters.TEXT & filters.ChatType.PRIVATE,
    user_message
))

# группа саппорта
app.add_handler(MessageHandler(
    filters.TEXT & filters.ChatType.GROUPS,
    support_reply
))

app.add_handler(CallbackQueryHandler(callback))

app.run_polling()
