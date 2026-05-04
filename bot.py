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
    assigned_to INTEGER
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

# ---------------- TICKETS ----------------
def create_ticket(user_id, username, message):
    cursor.execute("""
    INSERT INTO tickets (user_id, username, message, status, history, created_at, assigned_to)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, username, message, "NEW", message, now_str(), None))
    conn.commit()
    return cursor.lastrowid

def get_ticket(ticket_id):
    cursor.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,))
    return cursor.fetchone()

def update_status(ticket_id, status):
    cursor.execute("UPDATE tickets SET status=? WHERE id=?", (status, ticket_id))
    conn.commit()

def update_history(ticket_id, text):
    cursor.execute("SELECT history FROM tickets WHERE id=?", (ticket_id,))
    h = cursor.fetchone()[0] or ""
    h += f"\nSUPPORT: {text}"
    cursor.execute("UPDATE tickets SET history=? WHERE id=?", (h, ticket_id))
    conn.commit()

# ---------------- UI ----------------
def buttons(ticket_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Ответить", callback_data=f"reply_{ticket_id}")],
        [InlineKeyboardButton("🔀 Передать", callback_data=f"transfer_{ticket_id}")],
        [InlineKeyboardButton("⏳ На рассмотрении…", callback_data=f"wait_{ticket_id}")],
        [InlineKeyboardButton("🔒 Закрыть", callback_data=f"close_{ticket_id}")],
        [InlineKeyboardButton("🔇 Мут 1 час", callback_data=f"mute_{ticket_id}")],
        [InlineKeyboardButton("📵 Бан 3 дня", callback_data=f"ban_{ticket_id}")]
    ])

# ---------------- COMMAND ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📩 Здравствуйте! Опишите суть вашей проблемы.")

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
            await update.message.reply_text("🔇 Вам времено ограничен доступ к чату")
            return

    # антиспам (3 минуты)
    if data and data[3]:
        last = datetime.strptime(data[3], "%Y-%m-%d %H:%M:%S")
        if now() - last < timedelta(minutes=3):
            await update.message.reply_text("⏳ Подождите 3 минуты перед новым обращением")
            return

    update_user(user.id, last_ticket=now_str())

    ticket_id = create_ticket(user.id, user.first_name, update.message.text)

    await context.bot.send_message(
        chat_id=SUPPORT_CHAT_ID,
        text=f"🎫 Тикет #{ticket_id}\n👤 {user.first_name}\n\n{update.message.text}",
        reply_markup=buttons(ticket_id)
    )

    await update.message.reply_text("✅ Обращение отправлено! Ожидайте ответ саппорта")

# ---------------- CALLBACK ----------------
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, ticket_id = query.data.split("_")
    ticket_id = int(ticket_id)

    ticket = get_ticket(ticket_id)
    if not ticket:
        return

    user_id = ticket[1]
    assigned = ticket[7]

    # -------- REPLY --------
    if action == "reply":
        if assigned and assigned != query.from_user.id:
            await query.message.reply_text("⚔️ Это не ваш тикет")
            return

        cursor.execute("UPDATE tickets SET assigned_to=? WHERE id=?",
                       (query.from_user.id, ticket_id))
        conn.commit()

        context.user_data["reply_ticket"] = ticket_id
        await query.message.reply_text("✍️ Напишите ответ")
        return

    # -------- TRANSFER --------
    if action == "transfer":
        cursor.execute("UPDATE tickets SET assigned_to=NULL WHERE id=?", (ticket_id,))
        conn.commit()

        await query.message.reply_text("⚡ Тикет освобождён")
        return

    # -------- WAIT --------
    if action == "wait":
        update_status(ticket_id, "WAITING")

        await context.bot.send_message(user_id, "🔎 Ваш тикет на рассмотрении…")
        return

    # -------- CLOSE --------
    if action == "close":
        update_status(ticket_id, "CLOSED")

        await context.bot.send_message(user_id, "🔐 Ваш тикет был закрыт.")
        return

    # -------- MUTE --------
    if action == "mute":
        until = now() + timedelta(minutes=60)
        update_user(user_id, muted=until.strftime("%Y-%m-%d %H:%M:%S"))

        await context.bot.send_message(user_id, "🔇 Вы получили мут на 10 минут")
        await query.message.reply_text("🔇 Пользователь замучен")
        return

    # -------- BAN --------
    if action == "ban":
        until = now() + timedelta(hours=72)
        update_user(user_id, banned=until.strftime("%Y-%m-%d %H:%M:%S"))

        await query.message.reply_text("📵 Пользователь забанен")
        return

# ---------------- SUPPORT REPLY ----------------
async def support_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "reply_ticket" not in context.user_data:
        return

    ticket_id = context.user_data["reply_ticket"]
    text = update.message.text

    ticket = get_ticket(ticket_id)
    if not ticket:
        return

    user_id = ticket[1]
    owner = ticket[7]

    if owner != update.message.from_user.id:
        await update.message.reply_text("⚔️ Это не ваш тикет")
        return

    await context.bot.send_message(
        chat_id=user_id,
        text=f"📩 Ответ поддержки:\n\n{text}"
    )

    update_history(ticket_id, text)

    await update.message.reply_text("✅ Отправлено")
    del context.user_data["reply_ticket"]

# ---------------- APP ----------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.User(SUPPORT_CHAT_ID), user_message))
app.add_handler(MessageHandler(filters.TEXT & filters.User(SUPPORT_CHAT_ID), support_reply))
app.add_handler(CallbackQueryHandler(callback))

app.run_polling()
