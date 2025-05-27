from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.storage import get_channels

def get_admin_membership_menu():
    keyboard = [
        [InlineKeyboardButton("افزودن➕️", callback_data="add_channel"),
         InlineKeyboardButton("حذف➖️", callback_data="remove_channel")],
        [InlineKeyboardButton("برگشت🔙", callback_data="back_to_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_membership_check_keyboard():
    channels = get_channels()
    keyboard = [[InlineKeyboardButton(f"کانال {i+1}", url=f"https://t.me/{ch.strip('@')}")] for i, ch in enumerate(channels)]
    if channels:
        keyboard.append([InlineKeyboardButton("تایید عضویت✅️", callback_data="verify_membership")])
    return InlineKeyboardMarkup(keyboard)
