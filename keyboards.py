from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def user_start_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Задать вопрос", callback_data="new_ticket")]])

def user_cancel_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="cancel")]])

def support_kb(tid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Ответить", callback_data=f"reply_{tid}")],
        [InlineKeyboardButton("🔄 Передать", callback_data=f"transfer_{tid}")],
        [InlineKeyboardButton("⏳ Ожидание", callback_data=f"wait_{tid}")],
        [InlineKeyboardButton("🔐 Закрыть", callback_data=f"close_{tid}")],
        [InlineKeyboardButton("🔇 Мут 1ч", callback_data=f"mute_{tid}")],
        [InlineKeyboardButton("📵 Бан 3д", callback_data=f"ban_{tid}")]
    ])
