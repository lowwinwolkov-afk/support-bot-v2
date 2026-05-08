from telegram import Update
from telegram.ext import ContextTypes
from db import (
    get_ticket, assign_ticket, close_ticket,
    set_tag, set_first_response, set_user
)
from keyboards import ticket_kb, tag_menu
from config import SUPPORTS
from utils import add_hours, add_days, fmt

# ---------------- CALLBACK ----------------

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data
    action, tid = data.split("_")
    tid = int(tid)

    ticket = get_ticket(tid)
    if not ticket:
        return

    user_id = ticket[1]
    support_id = q.from_user.id
    support_name = SUPPORTS.get(support_id)

    # ---------------- TAKE ----------------
    if action == "take":

        if ticket[4] == "IN_PROGRESS":
            await q.message.reply_text("❌ Уже в работе")
            return

        assign_ticket(tid, support_id)
        set_first_response(tid)

        await context.bot.send_message(
            user_id,
            f"🛠 Саппорт {support_name} начал обработку тикета #{tid}"
        )

        await q.message.edit_text(
            f"🟢 IN_PROGRESS #{tid}\n👨‍💻 {support_name}",
            reply_markup=ticket_kb(tid)
        )

    # ---------------- CLOSE ----------------
    elif action == "close":
        close_ticket(tid)

        await context.bot.send_message(user_id, f"❌ Тикет #{tid} закрыт")
        await q.message.edit_text(f"🔴 CLOSED #{tid}")

    # ---------------- WAIT ----------------
    elif action == "wait":
        await context.bot.send_message(user_id, f"⏳ Тикет #{tid} в ожидании")

    # ---------------- TAG ----------------
    elif action == "tagmenu":
        await q.message.reply_text("🏷 Выберите тег:", reply_markup=tag_menu(tid))

    elif action == "tag":
        tag = tid
        set_tag(tid, tag)
        await q.message.edit_text(f"🏷 Тег установлен: {tag}")

    # ---------------- MUTE ----------------
    elif action == "mute":
        set_user(user_id, "muted_until", add_hours(1))
        await context.bot.send_message(user_id, "🔇 Мут 1 час")

    # ---------------- BAN ----------------
    elif action == "ban":
        set_user(user_id, "banned_until", add_days(3))
        await context.bot.send_message(user_id, "📵 Бан 3 дня")

    # ---------------- TRANSFER ----------------
    elif action == "transfer":
        assign_ticket(tid, None)
        await context.bot.send_message(user_id, f"🔄 Тикет #{tid} передан")
