import os
import random
import tempfile
import asyncio
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, TextClip

TOKEN = "7009887131:AAGEEW5TmkIAW77EuUnnZ1mxpksS_pKGGj4"
BASE_URL = "https://upload-2-fv80.onrender.com"

app = Flask(__name__)
user_state = {}

# === Tag Image Generator ===
def generate_tag_image(size=(300, 90)):
    text1 = TextClip("تلگرام", fontsize=32, font="Arial-Bold", color='white', method='caption')
    text2 = TextClip("kos_zx", fontsize=26, font="Arial-Bold", color='white', method='caption')
    text1 = text1.set_position(("center", "top")).set_duration(5)
    text2 = text2.set_position(("center", "bottom")).set_duration(5)
    bg = TextClip(" ", size=size, bg_color="black").set_opacity(0.5).set_duration(5)
    tag = CompositeVideoClip([bg, text1, text2], size=size)
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tag.save_frame(temp.name, t=0)
    return temp.name

def get_tag_size(label):
    return {"کوچیک": (200, 60), "متوسط": (300, 90), "بزرگ": (400, 120)}.get(label, (300, 90))

def add_static_tag(video_path, output_path, repeat, duration, size):
    tag_img = generate_tag_image(get_tag_size(size))
    clip = VideoFileClip(video_path)
    clips = [clip]
    for _ in range(repeat):
        start = random.uniform(0.1, max(0.1, clip.duration - duration - 1))
        pos = (random.randint(0, clip.w - get_tag_size(size)[0]), random.randint(0, clip.h - get_tag_size(size)[1]))
        tag = ImageClip(tag_img).set_duration(duration).set_start(start).set_position(pos).fadein(1).fadeout(1)
        clips.append(tag)
    final = CompositeVideoClip(clips)
    final.write_videofile(output_path, codec="libx264", audio_codec="aac")
    os.remove(tag_img)

def add_moving_tag(video_path, output_path):
    tag_img = generate_tag_image()
    clip = VideoFileClip(video_path)
    tag = ImageClip(tag_img).set_duration(clip.duration).set_position(
        lambda t: (
            int((clip.w / 2) + (clip.w / 3) * random.uniform(-1, 1) * (1 - t / clip.duration)),
            int((clip.h / 2) + (clip.h / 3) * random.uniform(-1, 1) * (1 - t / clip.duration))
        )
    ).fadein(1).fadeout(1)
    final = CompositeVideoClip([clip, tag])
    final.write_videofile(output_path, codec="libx264", audio_codec="aac")
    os.remove(tag_img)

# === Telegram Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 خوش اومدی! فقط کافیه فیلم بفرستی.")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    user_state[uid] = {"video_file_id": update.message.video.file_id, "step": "await_tag_type"}
    await update.message.reply_text("چه مدلی تگ می‌خوای؟", reply_markup=ReplyKeyboardMarkup([["ثابت", "متحرک"]], one_time_keyboard=True))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    state = user_state.get(uid)
    if not state:
        await update.message.reply_text("اول باید ویدیو بفرستی.")
        return

    msg = update.message.text
    if state["step"] == "await_tag_type":
        if msg == "ثابت":
            state["tag_type"] = msg
            state["step"] = "ask_repeat"
            await update.message.reply_text("چندبار تگ بیاد و بره؟", reply_markup=ReplyKeyboardMarkup([["1", "2", "3"], ["4", "5", "6"]], one_time_keyboard=True))
        elif msg == "متحرک":
            await update.message.reply_text("⏳ در حال پردازش...")
            state["step"] = "processing"
            await process_moving(update, context, state)
        return

    if state["step"] == "ask_repeat":
        state["repeat"] = int(msg)
        state["step"] = "ask_duration"
        await update.message.reply_text("هر تگ چند ثانیه نمایش داده شه؟", reply_markup=ReplyKeyboardMarkup([["3", "5", "10"]], one_time_keyboard=True))
        return

    if state["step"] == "ask_duration":
        state["duration"] = int(msg)
        state["step"] = "ask_size"
        await update.message.reply_text("اندازه تگ؟", reply_markup=ReplyKeyboardMarkup([["کوچیک", "متوسط", "بزرگ"]], one_time_keyboard=True))
        return

    if state["step"] == "ask_size":
        state["size"] = msg
        state["step"] = "processing"
        await update.message.reply_text("⏳ در حال پردازش...")
        await process_static(update, context, state)

async def process_static(update, context, state):
    uid = update.message.from_user.id
    file = await context.bot.get_file(state["video_file_id"])
    temp_in = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    await file.download_to_drive(temp_in)
    add_static_tag(temp_in, temp_out, state["repeat"], state["duration"], state["size"])
    await update.message.reply_video(video=open(temp_out, "rb"))
    os.remove(temp_in)
    os.remove(temp_out)
    user_state.pop(uid, None)

async def process_moving(update, context, state):
    uid = update.message.from_user.id
    file = await context.bot.get_file(state["video_file_id"])
    temp_in = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    await file.download_to_drive(temp_in)
    add_moving_tag(temp_in, temp_out)
    await update.message.reply_video(video=open(temp_out, "rb"))
    os.remove(temp_in)
    os.remove(temp_out)
    user_state.pop(uid, None)

# === Bot setup ===
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.VIDEO, handle_video))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        asyncio.create_task(application.process_update(update))
    except Exception as e:
        print("Error in webhook:", e)
    return "ok"

@app.route("/")
def home():
    return "Bot is up!"

if __name__ == "__main__":
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        webhook_url=f"{BASE_URL}/{TOKEN}"
    )
