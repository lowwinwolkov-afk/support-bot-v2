from telegram import Update
from telegram.ext import ContextTypes
from db import create_ticket, set_thread, get_user, set_user
from keyboards import user_start
from config import GROUP_ID
from utils import fmt

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет!\nОпишите проблему и мы ответим.",
        reply_markup=user_start()
    )


async def user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    text = update.message.text

    # антиспам
    u = get_user(user.id)
    if u and u[1]:
        from datetime import datetime, timedelta
        last = datetime.strptime(u[1], "%Y-%m-%d %H:%M:%S")
        if (datetime.now() - last).seconds < 180:
            return

    set_user(user.id, "last_message_time", fmt())

    tid = create_ticket(user.id, user.first_name, text)

    topic = await context.bot.create_forum_topic(
    chat_id=GROUP_ID,
    name=f"🆕 Ticket #{tid}"
)

thread_id = topic.message_thread_id

    await context.bot.send_message(
        chat_id=GROUP_ID,
        message_thread_id=topic.message_thread_id,
        text=f"🆕 NEW TICKET #{tid}\n\n👤 {user.first_name}\n\n{text}"
    )

    await update.message.reply_text(f"✅ Тикет #{tid} создан")
