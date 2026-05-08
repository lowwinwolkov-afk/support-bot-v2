from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def user_start():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🆕 Новый тикет", callback_data="new_ticket")]
    ])


def ticket_kb(tid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Взять", callback_data=f"take_{tid}")],
        [InlineKeyboardButton("🔄 Передать", callback_data=f"transfer_{tid}")],
        [InlineKeyboardButton("⏳ Ожидание", callback_data=f"wait_{tid}")],
        [InlineKeyboardButton("🔐 Закрыть", callback_data=f"close_{tid}")],
        [InlineKeyboardButton("🏷 Тег", callback_data=f"tagmenu_{tid}")],
        [InlineKeyboardButton("🔇 Мут 1ч", callback_data=f"mute_{tid}")],
        [InlineKeyboardButton("📵 Бан 3д", callback_data=f"ban_{tid}")]
    ])


def tag_menu(tid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💸 Оплата", callback_data=f"tag_payment_{tid}")],
        [InlineKeyboardButton("🐛 Баг", callback_data=f"tag_bug_{tid}")],
        [InlineKeyboardButton("📢 Идея", callback_data=f"tag_idea_{tid}")]
    ])
