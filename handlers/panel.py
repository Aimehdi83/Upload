from telegram import Update
from telegram.ext import ContextTypes
from keyboards.inline import get_admin_membership_menu
from config import ADMINS

async def panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMINS:
        return
    await update.message.reply_text("سلام آقای مدیر", reply_markup=get_admin_membership_menu())
