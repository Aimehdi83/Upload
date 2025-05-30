import os
import random
import tempfile
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, TextClip

TOKEN = "7009887131:AAHdcXnMmGZeJpn9d4RDklt2RdpIg49i2uU"
BASE_URL = "https://upload-2-fv80.onrender.com"

app = Flask(__name__)
user_state = {}

# === Image Generation ===
def generate_tag_image(size=(300, 90)):
    text1 = TextClip("تلگرام", fontsize=32, font="Arial-Bold", color='white', method='caption')
    text2 = TextClip("kos_zx", fontsize=26, font="Arial-Bold", color='white', method='caption')
    text1 = text1.set_position(("center", "top")).set_duration(5)
    text2 = text2.set_position(("center", "bottom")).set_duration(5)
    width, height = size
    bg = TextClip(" ", size=size, bg_color="black").set_opacity(0.5).set_duration(5)
    tag = CompositeVideoClip([bg, text1, text2], size=size)
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tag.save_frame(temp.name, t=0)
    return temp.name

# === Video Effects ===
def get_tag_size(size_label):
    return {
        "کوچیک": (200, 60),
        "متوسط": (300, 90),
        "بزرگ": (400, 120)
    }.get(size_label, (300, 90))

def add_static_tag(video_path, output_path, repeat, duration, size):
    tag_img_path = generate_tag_image(size=get_tag_size(size))
    clip = VideoFileClip(video_path)
    clips = [clip]
    for _ in range(repeat):
        start = random.uniform(0.1, max(0.1, clip.duration - duration - 1))
        pos = (random.randint(0, clip.w - get_tag_size(size)[0]), random.randint(0, clip.h - get_tag_size(size)[1]))
        tag = (ImageClip(tag_img_path)
               .set_duration(duration)
               .set_start(start)
               .set_position(pos)
               .fadein(1.5).fadeout(1.5))
        clips.append(tag)
    final = CompositeVideoClip(clips)
    final.write_videofile(output_path, codec="libx264", audio_codec="aac")
    os.remove(tag_img_path)

def add_moving_tag(video_path, output_path):
    tag_img_path = generate_tag_image()
    clip = VideoFileClip(video_path)
    tag = (ImageClip(tag_img_path)
           .set_duration(clip.duration)
           .set_position(lambda t: (
               int((clip.w / 2) + (clip.w / 3) * random.uniform(-1, 1) * random.choice([1, -1]) * (1 - t / clip.duration)),
               int((clip.h / 2) + (clip.h / 3) * random.uniform(-1, 1) * random.choice([1, -1]) * (1 - t / clip.duration))
           ))
           .fadein(1.5).fadeout(1.5))
    final = CompositeVideoClip([clip, tag])
    final.write_videofile(output_path, codec="libx264", audio_codec="aac")
    os.remove(tag_img_path)

# === Telegram Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 خوش اومدی! فقط کافیه فیلم بفرستی تا شروع کنیم.")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_state[user_id] = {"video_file_id": update.message.video.file_id, "step": "await_tag_type"}
    await update.message.reply_text("دریافت شد. چه مدلی تگ می‌خوای؟", reply_markup=ReplyKeyboardMarkup([["ثابت", "متحرک"]], one_time_keyboard=True))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    state = user_state.get(user_id, {})
    if not state:
        await update.message.reply_text("اول باید فیلم بفرستی.")
        return

    if state.get("step") == "await_tag_type":
        state["tag_type"] = update.message.text
        if update.message.text == "ثابت":
            state["step"] = "ask_repeat"
            await update.message.reply_text("🔁 چندبار تگ بیاد و بره؟", reply_markup=ReplyKeyboardMarkup([["1", "2", "3"], ["4", "5", "6"]], one_time_keyboard=True))
        elif update.message.text == "متحرک":
            state["step"] = "processing"
            await update.message.reply_text("⏳ در حال آماده‌سازی... لطفاً صبر کنید.")
            await process_moving_tag(update, context, state)
        user_state[user_id] = state
        return

    if state.get("step") == "ask_repeat":
        state["repeat"] = int(update.message.text)
        state["step"] = "ask_duration"
        await update.message.reply_text("⏱ هر تگ چند ثانیه نمایش داده شود؟", reply_markup=ReplyKeyboardMarkup([["3", "5", "10"]], one_time_keyboard=True))
        return

    if state.get("step") == "ask_duration":
        state["duration"] = int(update.message.text)
        state["step"] = "ask_size"
        await update.message.reply_text("📏 اندازه تگ؟", reply_markup=ReplyKeyboardMarkup([["کوچیک", "متوسط", "بزرگ"]], one_time_keyboard=True))
        return

    if state.get("step") == "ask_size":
        state["size"] = update.message.text
        state["step"] = "processing"
        await update.message.reply_text("⏳ در حال آماده‌سازی... لطفاً صبر کنید.")
        await process_static_tag(update, context, state)
        return

async def process_static_tag(update: Update, context: ContextTypes.DEFAULT_TYPE, state):
    user_id = update.message.from_user.id
    video_file = await context.bot.get_file(state["video_file_id"])
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_in:
        await video_file.download_to_drive(temp_in.name)
    temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    add_static_tag(temp_in.name, temp_out, state["repeat"], state["duration"], state["size"])
    await update.message.reply_video(video=open(temp_out, "rb"))
    os.remove(temp_in.name)
    os.remove(temp_out)
    user_state.pop(user_id, None)

async def process_moving_tag(update: Update, context: ContextTypes.DEFAULT_TYPE, state):
    user_id = update.message.from_user.id
    video_file = await context.bot.get_file(state["video_file_id"])
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_in:
        await video_file.download_to_drive(temp_in.name)
    temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    add_moving_tag(temp_in.name, temp_out)
    await update.message.reply_video(video=open(temp_out, "rb"))
    os.remove(temp_in.name)
    os.remove(temp_out)
    user_state.pop(user_id, None)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "ok"

@app.route("/")
def index():
    return "Bot is running."

application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.VIDEO, handle_video))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

if __name__ == "__main__":
    application.run_webhook(listen="0.0.0.0", port=int(os.environ.get("PORT", 5000)), webhook_url=f"{BASE_URL}/{TOKEN}")
