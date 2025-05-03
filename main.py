import asyncio
import json
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

ADMINS = [5459406429, 6387942633]
VIDEO, CAPTION = range(2)
video_store = {}

# بارگذاری داده‌های قبلی از فایل JSON
def load_video_data():
    try:
        with open('videos.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# ذخیره داده‌های جدید به فایل JSON
def save_video_data():
    with open('videos.json', 'w') as file:
        json.dump(video_store, file)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args:
        key = args[0]
        file_id = video_store.get(key)
        if file_id:
            sent = await update.message.reply_video(video=file_id)
            await asyncio.sleep(20)
            try:
                await sent.delete()
            except:
                pass
        else:
            await update.message.reply_text("ویدیو یافت نشد.")
    elif update.effective_user.id in ADMINS:
        await update.message.reply_text("لطفاً یک ویدیو ارسال کنید.")
        return VIDEO
    else:
        await update.message.reply_text("شما دسترسی ندارید.")
        return ConversationHandler.END

async def receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        key = str(len(video_store) + 1)
        video_store[key] = file_id
        save_video_data()  # ذخیره داده‌های جدید
        context.user_data['video_id'] = file_id
        context.user_data['key'] = key
        await update.message.reply_text("کپشن ویدیو را وارد کنید:")
        return CAPTION
    else:
        await update.message.reply_text("لطفاً یک ویدیو معتبر ارسال کنید.")
        return VIDEO

async def receive_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.text
    file_id = context.user_data['video_id']
    key = context.user_data['key']
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={key}"

    full_caption = (
        f"{caption}\n\n"
        f"[مشاهده]({link})\n\n"
        f"🔥@hottof | تُفِ داغ"
    )

    await update.message.reply_text("پیام آماده‌سازی شد:")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=full_caption,
        parse_mode="Markdown"
    )

    await update.message.reply_text("ویدیو بعدی را ارسال کنید:")
    return VIDEO

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عملیات لغو شد.")
    return ConversationHandler.END

if __name__ == '__main__':
    from telegram.ext import defaults
    import logging
    logging.basicConfig(level=logging.INFO)

    # بارگذاری داده‌ها
    video_store = load_video_data()

    TOKEN = "8109192869:AAHAjLLrnDCFFjdocFmSeceFVUh6O4PpVeo"
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            VIDEO: [MessageHandler(filters.VIDEO, receive_video)],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_caption)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.run_polling()
