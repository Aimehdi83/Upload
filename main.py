import os
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from flask import Flask
import threading

ADMINS = [5459406429, 6387942633]
VIDEO, CAPTION = range(2)
video_store = {}

# سرور Flask برای زنده نگه داشتن Render
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!", 200

def run_web():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args:
        file_key = args[0]
        file_id = video_store.get(file_key)
        if file_id:
            sent = await update.message.reply_video(video=file_id)
            await asyncio.sleep(20)
            try:
                await sent.delete()
            except:
                pass
        else:
            await update.message.reply_text("ویدیو پیدا نشد.")
    elif update.effective_user.id in ADMINS:
        await update.message.reply_text("لطفاً ویدیو را ارسال کنید.")
        return VIDEO
    else:
        await update.message.reply_text("برای استفاده از ربات، روی لینک مشاهده کلیک کنید.")
        return ConversationHandler.END

async def receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        key = str(len(video_store) + 1)
        video_store[key] = file_id
        context.user_data['video_id'] = file_id
        context.user_data['video_key'] = key
        await update.message.reply_text("کپشن ویدیو را وارد کنید:")
        return CAPTION
    else:
        await update.message.reply_text("لطفاً یک ویدیو ارسال کنید.")
        return VIDEO

async def receive_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.text
    file_id = context.user_data['video_id']
    key = context.user_data['video_key']

    link = f"https://t.me/{{context.bot.username}}?start={{key}}"

    full_caption = (
        f"{{caption}}\n\n"
        f"[مشاهده]({{link}})\n\n"
        f"🔥@hottof | تُفِ داغ"
    )

    await update.message.reply_text("ویدیو با موفقیت منتشر شد:")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=full_caption,
        parse_mode='Markdown'
    )

    await update.message.reply_text("لطفاً ویدئوی بعدی را ارسال کنید:")
    return VIDEO

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("لغو شد.")
    return ConversationHandler.END

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)

    threading.Thread(target=run_web).start()

    TOKEN = "8109192869:AAHAjLLrnDCFFjdocFmSeceFVUh6O4PpVeo"
    app_bot = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            VIDEO: [MessageHandler(filters.VIDEO, receive_video)],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_caption)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )

    app_bot.add_handler(conv_handler)
    app_bot.run_polling()
