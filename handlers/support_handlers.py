from telegram import Update
from telegram.ext import ContextTypes
from keyboards import support_kb
from db import cursor, conn, now

SUPPORT_TOPICS = {}  # support_id: thread_id

async def support_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return
    text = update.message.text
    replied_text = update.message.reply_to_message.text
    if "Тикет #" not in replied_text:
        return
    tid = int(replied_text.split("#")[1].split("\n")[0])
    cursor.execute("SELECT user_id FROM tickets WHERE id=?", (tid,))
    user_id = cursor.fetchone()[0]
    await context.bot.send_message(user_id, f"👨‍💻 Ответ саппорта:\n{text}")

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    action, tid = q.data.split("_")
    tid = int(tid)

    # Тут логика take, transfer, wait, close, mute, ban
    # Каждая кнопка меняет статус в базе и уведомляет клиента
