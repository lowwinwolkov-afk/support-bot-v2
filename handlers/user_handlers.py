from telegram import Update
from telegram.ext import ContextTypes
from keyboards import user_start_kb, user_cancel_kb
from db import cursor, conn, now

USER_STATE = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    await update.message.reply_text(
        "👋 Привет! Я бот-помощник проекта Awesome Russia. Опишите вашу проблему и вам обязательно помогут🤗\n\n"
        "📋 Формат обращения:\n"
        "Ваш игровой никнейм\nВаш сервер\nСуть проблемы\nДата и время возникновения ошибки",
        reply_markup=user_start_kb()
    )

async def user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    # Создаем новый тикет
    cursor.execute("INSERT INTO tickets (user_id, username, message, status, created_at) VALUES (?,?,?,?,?)",
                   (user_id, update.message.from_user.first_name, text, "NEW", now()))
    conn.commit()
    tid = cursor.lastrowid

    await update.message.reply_text(f"✅ Ваш запрос принят. Ожидайте ответ саппорта. Номер тикета: #{tid}")

async def new_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 Подробно опишите вашу проблему:",
        reply_markup=user_cancel_kb()
    )
    USER_STATE[update.message.from_user.id] = "new_ticket"
