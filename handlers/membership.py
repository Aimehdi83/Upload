from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from keyboards.inline import get_admin_membership_menu, get_membership_check_keyboard
from utils.storage import add_channel, remove_channel, get_channels
from utils.checker import check_user_membership
from config import ADMINS

# حافظه موقت برای انتظار آیدی کانال از ادمین‌ها
waiting_for = {}

async def membership_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    # فقط ادمین
    if query.data in ["add_channel", "remove_channel"] and user_id not in ADMINS:
        return

    if query.data == "add_channel":
        waiting_for[user_id] = "adding"
        await query.message.edit_text("اول منو ادمین کانال کن و بعدش آیدی کانال رو بفرست (مثلاً @channel)")
        return

    if query.data == "remove_channel":
        waiting_for[user_id] = "removing"
        await query.message.edit_text("آیدی کانالی که می‌خوای حذف کنی رو بفرست (مثلاً @channel)")
        return

    if query.data == "back_to_panel":
        await query.message.edit_text("سلام آقای مدیر", reply_markup=get_admin_membership_menu())
        return

    if query.data == "verify_membership":
        user = query.from_user
        full = await check_user_membership(user.id, context.bot)
        if full:
            await query.message.delete()
            await query.message.chat.send_message("عضویت شما تایید شد ✅️")
        else:
            channels = get_channels()
            unjoined = []
            for ch in channels:
                try:
                    member = await context.bot.get_chat_member(ch, user.id)
                    if member.status not in ["member", "administrator", "creator"]:
                        unjoined.append(ch)
                except:
                    unjoined.append(ch)
            keyboard = [
                [InlineKeyboardButton(f"کانال {i+1}", url=f"https://t.me/{ch.strip('@')}")] 
                for i, ch in enumerate(unjoined)
            ]
            keyboard.append([InlineKeyboardButton("تایید عضویت✅️", callback_data="verify_membership")])
            await query.message.reply_text(
                "⚠️ شما هنوز در همه کانال‌ها عضو نشده‌اید", 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
