from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from config import TOKEN
from user_handlers import start, user_message
from support_handlers import callback

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))

app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, user_message))

app.add_handler(CallbackQueryHandler(callback))

app.run_polling()
