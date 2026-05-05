import sqlite3
from datetime import datetime, timedelta
from telegram import *
from telegram.ext import *

TOKEN = "8288994829:AAHh5SqqJyWe_3gskGRz10sv5vLyw9ryBf0"
GROUP_ID = -1003979602444

NEW_TICKETS_TOPIC = 42
LOG_TOPIC = 44

# user_id саппорта → thread_id темы
SUPPORT_THREADS = {
    5530223549: 5,
    987654321: 7
}

IGNORE_TOPICS = [1, 4]

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

conn.commit()

# ---------------- UTILS ----------------
def fmt():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_ticket(tid):
    cursor.execute("SELECT * FROM tickets WHERE id=?", (tid,))
    return cursor.fetchone()

# ---------------- UI ----------------
def start_kb():
    return ReplyKeyboardMarkup([
        ["🆕 Новый тикет"]
    ], resize_keyboard=True)

def ticket_kb(tid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Взять", callback_data=f"take_{tid}")],
        [InlineKeyboardButton("🔄 Передать", callback_data=f"transfer_{tid}")],
        [InlineKeyboardButton("⏳ Ожидание", callback_data=f"wait_{tid}")],
        [InlineKeyboardButton("❌ Закрыть", callback_data=f"close_{tid}")],
        [InlineKeyboardButton("🔇 Мут1ч", callback_data=f"mute_{tid}")],
        [InlineKeyboardButton("⛔ Бан 3д", callback_data=f"ban_{tid}")]
    ])

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Добро пожаловать в саппорт\n\n"
        "📌 Правила:\n"
        "• Не спамить\n"
        "• Не оскорблять\n"
        "• Чётко описывать проблему\n\n"
        "📋 Шаблон:\n"
        "1. Ник\n"
        "2. Сервер\n"
        "3. Проблема\n"
        "4. Дата/время"
    )

    await update.message.reply_text(text, reply_markup=start_kb())

# ---------------- USER ----------------
async def user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.message.from_user

    # нажал "новый тикет"
    if text == "🆕 Новый тикет":
        await start(update, context)
        return

    # создаём тикет
    cursor.execute("""
    INSERT INTO tickets (user_id, username, message, status, assigned_to, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user.id, user.first_name, text, "NEW", None, fmt()))
    conn.commit()

    tid = cursor.lastrowid

    await context.bot.send_message(
        chat_id=GROUP_ID,
        message_thread_id=NEW_TICKETS_TOPIC,
        text=f"🎫 Тикет #{tid}\n👤 {user.first_name}\n\n{text}",
        reply_markup=ticket_kb(tid)
    )

    await update.message.reply_text("✅ Тикет отправлен")

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
    support_id = q.from_user.id
    support_name = q.from_user.first_name

    # -------- TAKE --------
    if action == "take":

        if ticket[5]:
            await q.message.reply_text("❌ Уже взят")
            return

        cursor.execute(
            "UPDATE tickets SET assigned_to=?, status=? WHERE id=?",
            (support_id, "IN_PROGRESS", tid)
        )
        conn.commit()

        # уведомление пользователю
        await context.bot.send_message(
            user_id,
            f"🛠 Саппорт {support_name} начал обработку тикета #{tid}"
        )

        # перенос в тему саппорта
        thread_id = SUPPORT_THREADS.get(support_id)

        if thread_id:
            await context.bot.send_message(
                GROUP_ID,
                message_thread_id=thread_id,
                text=f"🎫 Тикет #{tid}\n👤 {ticket[2]}\n\n{ticket[3]}",
                reply_markup=ticket_kb(tid)
            )

        # редактируем старое сообщение
        try:
            await q.message.edit_text(
                f"✅ Тикет #{tid}\n🛠 Обрабатывает: {support_name}"
            )
        except:
            pass

        # лог
        await context.bot.send_message(
            GROUP_ID,
            message_thread_id=LOG_TOPIC,
            text=f"📊 {support_name} взял тикет #{tid}"
        )

    # -------- TRANSFER --------
    elif action == "transfer":
        cursor.execute("UPDATE tickets SET assigned_to=NULL WHERE id=?", (tid,))
        conn.commit()

        await q.message.reply_text("🔄 Тикет передан")

    # -------- WAIT --------
    elif action == "wait":
        await context.bot.send_message(user_id, "⏳ Ваш тикет в ожидании")

    # -------- CLOSE --------
    elif action == "close":
        cursor.execute("UPDATE tickets SET status=? WHERE id=?", ("CLOSED", tid))
        conn.commit()

        await context.bot.send_message(user_id, "❌ Тикет закрыт")

    # -------- MUTE --------
    elif action == "mute":
        await context.bot.send_message(user_id, "🔇 Вы получили мут")

    # -------- BAN --------
    elif action == "ban":
        await context.bot.send_message(user_id, "⛔ Вы забанены")

# ---------------- SUPPORT REPLY ----------------
async def support_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.message_thread_id in IGNORE_TOPICS:
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

# ---------------- APP ----------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))

app.add_handler(MessageHandler(
    filters.TEXT & filters.ChatType.PRIVATE,
    user_message
))

app.add_handler(MessageHandler(
    filters.TEXT & filters.ChatType.GROUPS,
    support_reply
))

app.add_handler(CallbackQueryHandler(callback))

app.run_polling()
