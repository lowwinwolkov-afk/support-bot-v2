from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from handlers.user_handlers import start, user_message, new_ticket
from handlers.support_handlers import callback, support_reply

TOKEN = "8288994829:AAHh5SqqJyWe_3gskGRz10sv5vLyw9ryBf0"

app = ApplicationBuilder().token(TOKEN).build()

# Пользовательский интерфейс
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, user_message))
app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, new_ticket))

# Чат саппорта
app.add_handler(MessageHandler(filters.TEXT, support_reply))
app.add_handler(CallbackQueryHandler(callback))

app.run_polling()
