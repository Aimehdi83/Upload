from utils.storage import get_channels
from telegram import Bot

async def check_user_membership(user_id, bot: Bot):
    channels = get_channels()
    for channel in channels:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True
