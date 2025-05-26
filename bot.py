import logging
import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np
import joblib
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)

# تنظیم لاگ‌ها
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = '7009887131:AAEQE2NiromIjaD8ulRt99nRQt7DAFp-VQE'

# فایل‌های داده و مدل
DATA_FILE = 'data.csv'
MODEL_FILE = 'model.pkl'

# مراحل گفتگو (برای ادمین و کاربر)
(
    ADMIN_ADD_BIO, ADMIN_ADD_CHEM, ADMIN_ADD_PHYS, ADMIN_ADD_MATH, ADMIN_ADD_SCORE,
    USER_BIO, USER_CHEM, USER_PHYS, USER_MATH
) = range(9)

# چک کردن ادمین (آی‌دی شما رو بزار)
ADMIN_IDS = [7375505910]  # اینجا ایدی تلگرام ادمین رو بزار

# بارگذاری داده‌ها
def load_data():
    try:
        df = pd.read_csv(DATA_FILE)
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=['biology','chemistry','physics','math','score'])

# افزودن رکورد جدید
def add_record(bio, chem, phys, math, score):
    df = load_data()
    new_data = {'biology': bio, 'chemistry': chem, 'physics': phys, 'math': math, 'score': score}
    df = df.append(new_data, ignore_index=True)
    df.to_csv(DATA_FILE, index=False)

# آموزش مدل
def train_model():
    df = load_data()
    if len(df) < 5:
        return False, "داده کافی برای آموزش وجود ندارد."
    X = df[['biology','chemistry','physics','math']]
    y = df['score']
    model = LinearRegression()
    model.fit(X, y)
    joblib.dump(model, MODEL_FILE)
    return True, "مدل با موفقیت آموزش داده شد."

# پیش‌بینی تراز
def predict_score(bio, chem, phys, math):
    try:
        model = joblib.load(MODEL_FILE)
    except FileNotFoundError:
        return None
    X = np.array([[bio, chem, phys, math]])
    pred = model.predict(X)
    return round(pred[0], 2)

# چک ادمین
def is_admin(user_id):
    return user_id in ADMIN_IDS

# استارت برای همه
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_admin(user_id):
        keyboard = [
            [KeyboardButton("➕ افزودن کارنامه")],
            [KeyboardButton("🔄 هنگام‌سازی مدل")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("سلام ادمین! چه کاری انجام بدم؟", reply_markup=reply_markup)
    else:
        await update.message.reply_text("سلام! درصدهای زیست، شیمی، فیزیک و ریاضی خودت رو به ترتیب وارد کن (مثلاً: 70 60 80 90)")

# -- مسیر ادمین --

# شروع افزودن کارنامه جدید
async def admin_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("شما ادمین نیستید!")
        return ConversationHandler.END
    await update.message.reply_text("درصد زیست را وارد کنید:")
    return ADMIN_ADD_BIO

async def admin_add_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        bio = float(update.message.text)
        if not (0 <= bio <= 100):
            raise ValueError
        context.user_data['bio'] = bio
        await update.message.reply_text("درصد شیمی را وارد کنید:")
        return ADMIN_ADD_CHEM
    except ValueError:
        await update.message.reply_text("لطفا عددی بین 0 تا 100 وارد کنید:")
        return ADMIN_ADD_BIO

async def admin_add_chem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chem = float(update.message.text)
        if not (0 <= chem <= 100):
            raise ValueError
        context.user_data['chem'] = chem
        await update.message.reply_text("درصد فیزیک را وارد کنید:")
        return ADMIN_ADD_PHYS
    except ValueError:
        await update.message.reply_text("لطفا عددی بین 0 تا 100 وارد کنید:")
        return ADMIN_ADD_CHEM

async def admin_add_phys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        phys = float(update.message.text)
        if not (0 <= phys <= 100):
            raise ValueError
        context.user_data['phys'] = phys
        await update.message.reply_text("درصد ریاضی را وارد کنید:")
        return ADMIN_ADD_MATH
    except ValueError:
        await update.message.reply_text("لطفا عددی بین 0 تا 100 وارد کنید:")
        return ADMIN_ADD_PHYS

async def admin_add_math(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        math = float(update.message.text)
        if not (0 <= math <= 100):
            raise ValueError
        context.user_data['math'] = math
        await update.message.reply_text("تراز نهایی را وارد کنید:")
        return ADMIN_ADD_SCORE
    except ValueError:
        await update.message.reply_text("لطفا عددی معتبر وارد کنید:")
        return ADMIN_ADD_MATH

async def admin_add_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        score = float(update.message.text)
        context.user_data['score'] = score

        add_record(
            context.user_data['bio'],
            context.user_data['chem'],
            context.user_data['phys'],
            context.user_data['math'],
            context.user_data['score']
        )
        await update.message.reply_text("داده با موفقیت اضافه شد.")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("لطفا عددی معتبر وارد کنید:")
        return ADMIN_ADD_SCORE

# هنگام‌سازی مدل
async def retrain_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("شما ادمین نیستید!")
        return
    success, msg = train_model()
    await update.message.reply_text(msg)

# مسیر کاربر عادی: گرفتن درصدها و پیش‌بینی
async def user_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    parts = user_text.split()
    if len(parts) != 4:
        await update.message.reply_text("لطفا ۴ عدد درصد را با فاصله وارد کنید (مثلاً: 70 60 80 90)")
        return
    try:
        bio, chem, phys, math = map(float, parts)
        for val in (bio, chem, phys, math):
            if not (0 <= val <= 100):
                raise ValueError
        pred = predict_score(bio, chem, phys, math)
        if pred is None:
            await update.message.reply_text("مدل هنوز آموزش داده نشده است. لطفا از ادمین بخواهید مدل را هنگام‌سازی کند.")
        else:
            await update.message.reply_text(f"تراز تخمینی شما: {pred}")
    except ValueError:
        await update.message.reply_text("لطفا فقط عدد بین 0 تا 100 وارد کنید.")

# هندلر دکمه‌ها در منوی ادمین
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "➕ افزودن کارنامه":
        return await admin_add_start(update, context)
    elif text == "🔄 هنگام‌سازی مدل":
        return await retrain_model(update, context)
    else:
        await update.message.reply_text("دستور نامعتبر است.")

# تعریف ConversationHandler برای افزودن کارنامه ادمین
admin_conversation = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('^(➕ افزودن کارنامه)$'), button_handler)],
    states={
        ADMIN_ADD_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_bio)],
        ADMIN_ADD_CHEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_chem)],
        ADMIN_ADD_PHYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_phys)],
        ADMIN_ADD_MATH: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_math)],
        ADMIN_ADD_SCORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_score)],
    },
    fallbacks=[]
)

# هندلر دکمه هنگام‌سازی
retrain_handler = MessageHandler(filters.Regex('^(🔄 هنگام‌سازی مدل)$'), button_handler)

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(admin_conversation)
    app.add_handler(retrain_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_input_handler))

    print("ربات در حال اجراست...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
