from telegram import Update
from telegram.ext import ContextTypes
from utils.checker import check_user_membership
from keyboards.inline import get_membership_check_keyboard

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await check_user_membership(user.id, context.bot):
        await update.message.reply_text(
            "برای استفاده از ربات لطفا توی کانال های اسپانسر عضو شو",
            reply_markup=get_membership_check_keyboard()
        )
        return
    await update.message.reply_text("سلام خوش اومدی ✅")
