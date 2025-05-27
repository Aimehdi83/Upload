from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
import asyncio
import os

from handlers.start import start_handler
from handlers.panel import panel_handler
from handlers.membership import membership_callback_handler

TOKEN = os.getenv("BOT_TOKEN")  # توکن از متغیر محیطی
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"https://your-render-url.onrender.com/{TOKEN}"

bot = Bot(token=TOKEN)
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# ثبت هندلرها
application.add_handler(CommandHandler("start", start_handler))
application.add_handler(CommandHandler("panel", panel_handler))
application.add_handler(CallbackQueryHandler(membership_callback_handler))

# دریافت پیام وبهوک از تلگرام و انتقال به بات
@app.post(WEBHOOK_PATH)
async def webhook(request):
    if request.method == "POST":
        update = Update.de_json(await request.get_json(), bot)
        await application.process_update(update)
    return "ok", 200

# راه‌اندازی بات و ثبت وبهوک
@app.before_first_request
def init_bot():
    asyncio.get_event_loop().create_task(set_webhook())

async def set_webhook():
    await bot.set_webhook(WEBHOOK_URL)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
