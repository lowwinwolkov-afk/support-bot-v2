import sqlite3
from datetime import datetime, timedelta
from telegram import *
from telegram.ext import *

TOKEN = "8288994829:AAHh5SqqJyWe_3gskGRz10sv5vLyw9ryBf0"

GROUP_ID = -1003979602444

# 📌 ТОЛЬКО рабочие темы для бота
NEW_TICKETS_TOPIC = 42
LOG_TOPIC = 44

SUPPORT_TOPICS = {
    5: "LowWin",
    7: "Hellsinger"
    10: "Вакантно (1)"
    9: "Вакантно (2)"
    12: "Вакантно (3)"
}

# 🚫 ВАЖНО: эти темы бот ИГНОРИРУЕТ (флуд / инфо)
IGNORE_TOPICS = [4, 1]

# ---------------- DB ----------------
conn = sqlite3.connect("tickets.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    message TEXT,
    status TEXT,
    assigned_to INTEGER,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    muted_until TEXT,
    banned_until TEXT
)
""")

conn.commit()

# ---------------- UTILS ----------------
def now():
    return datetime.now()

def fmt():
    return now().strftime("%Y-%m-%d %H:%M:%S")

def get_ticket(tid):
    cursor.execute("SELECT * FROM tickets WHERE id=?", (tid,))
    return cursor.fetchone()

def update_user(uid, muted=None, banned=None):
    cursor.execute("""
    INSERT INTO users (user_id, muted_until, banned_until)
    VALUES (?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
    muted_until=COALESCE(?, muted_until),
    banned_until=COALESCE(?, banned_until)
    """, (uid, muted, banned, muted, banned))
    conn.commit()

# ---------------- UI ----------------
def kb(tid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Взять", callback_data=f"take_{tid}")],
        [InlineKeyboardButton("🔄 Передать", callback_data=f"transfer_{tid}")],
        [InlineKeyboardButton("⏳ Ожидание", callback_data=f"wait_{tid}")],
        [InlineKeyboardButton("🔐 Закрыть", callback_data=f"close_{tid}")],
        [InlineKeyboardButton("🔇 Мут 1ч", callback_data=f"mute_{tid}")],
        [InlineKeyboardButton("📵 Бан 3д", callback_data=f"ban_{tid}")]
    ])

# ---------------- USER ----------------
async def user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    cursor.execute("""
    INSERT INTO tickets (user_id, username, message, status, assigned_to, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user.id, user.first_name, update.message.text, "NEW", None, fmt()))
    conn.commit()

    tid = cursor.lastrowid

    # 📥 ТОЛЬКО сюда идут тикеты
    await context.bot.send_message(
        chat_id=GROUP_ID,
        message_thread_id=NEW_TICKETS_TOPIC,
        text=f"🎫 Тикет #{tid}\n👤 {user.first_name}\n\n{update.message.text}",
        reply_markup=kb(tid)
    )

    await update.message.reply_text("✅ Тикет отправлен! Ожидайте ответ саппорта")

# ---------------- CALLBACK ----------------
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    action, tid = q.data.split("_")
    tid = int(tid)

    ticket = get_ticket(tid)
    if not ticket:
        return

    user_id = ticket[1]
    support_name = q.from_user.first_name
    support_id = q.from_user.id

    # ---------------- TAKE ----------------
    if action == "take":

        if ticket[5]:
            await q.message.reply_text("❌ Уже обрабатывается другим саппортом")
            return

        cursor.execute(
            "UPDATE tickets SET assigned_to=?, status=? WHERE id=?",
            (support_id, "IN_PROGRESS", tid)
        )
        conn.commit()

        # 👤 уведомление пользователю
        await context.bot.send_message(
            user_id,
            f"🛠 Саппорт {support_name} взялся за ваш тикет #{tid}"
        )

        # 🧑‍💻 отправка в тему саппорта
        if support_id in SUPPORT_TOPICS:
            thread_id = list(SUPPORT_TOPICS.keys())[list(SUPPORT_TOPICS.values()).index(support_name)]

            await context.bot.send_message(
                GROUP_ID,
                message_thread_id=thread_id,
                text=f"🎫 Тикет #{tid}\n👤 {ticket[2]}\n\n{ticket[3]}\n\n👨‍💻 Взял: {support_name}"
            )

        # 📊 лог
        await context.bot.send_message(
            GROUP_ID,
            message_thread_id=LOG_TOPIC,
            text=f"📊 Тикет #{tid} взят {support_name}"
        )

    # ---------------- TRANSFER ----------------
    elif action == "transfer":
        cursor.execute("UPDATE tickets SET assigned_to=NULL WHERE id=?", (tid,))
        conn.commit()

        await context.bot.send_message(
            GROUP_ID,
            message_thread_id=LOG_TOPIC,
            text=f"🔄 Тикет #{tid} передан обратно в очередь"
        )

    # ---------------- WAIT ----------------
    elif action == "wait":
        await context.bot.send_message(user_id, f"⏳ Тикет #{tid} на рассмотрении…")

    # ---------------- CLOSE ----------------
    elif action == "close":
        cursor.execute("UPDATE tickets SET status=? WHERE id=?", ("CLOSED", tid))
        conn.commit()

        await context.bot.send_message(user_id, f"❌ Тикет #{tid} закрыт")

    # ---------------- MUTE ----------------
    elif action == "mute":
        until = now() + timedelta(minutes=60)
        update_user(user_id, muted=until.strftime("%Y-%m-%d %H:%M:%S"))

        await context.bot.send_message(user_id, "🔇 Мут на 60 минут")

    # ---------------- BAN ----------------
    elif action == "ban":
        until = now() + timedelta(hours=72)
        update_user(user_id, banned=until.strftime("%Y-%m-%d %H:%M:%S"))

        await context.bot.send_message(user_id, "⛔ Бан на 3 дня")

# ---------------- SUPPORT REPLY ----------------
async def support_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # ❌ игнорируем флуд / инфо темы
    thread_id = update.message.message_thread_id
    if thread_id in IGNORE_TOPICS:
        return

    if not update.message.reply_to_message:
        return

    text = update.message.reply_to_message.text

    if "Тикет #" not in text:
        return

    tid = int(text.split("#")[1].split("\n")[0])
    ticket = get_ticket(tid)

    if not ticket:
        return

    await context.bot.send_message(
        ticket[1],
        f"👨‍💻 {update.message.from_user.first_name}:\n\n{update.message.text}"
    )

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Опишите вашу проблему")

# ---------------- APP ----------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))

app.add_handler(MessageHandler(
    filters.TEXT & filters.ChatType.PRIVATE,
    user_message
))

app.add_handler(MessageHandler(filters.TEXT, support_reply))
app.add_handler(CallbackQueryHandler(callback))

app.run_polling()
