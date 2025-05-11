from flask import Flask, request
import requests
import threading
import time
from config import BOT_TOKEN, WEBHOOK_URL, ADMIN_IDS, CHANNEL_TAG, PING_INTERVAL
from database import save_file, get_file, add_force_channel, remove_force_channel, get_force_channels
from utils import gen_code

app = Flask(__name__)
URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
users = {}
pinging = True

def send(method, data):
    response = requests.post(f"{URL}/{method}", json=data).json()
    print(f"Response from {method}: {response}")
    return response

def delete(chat_id, message_id):
    send("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

def ping():
    while pinging:
        try:
            requests.get(WEBHOOK_URL)
        except:
            pass
        time.sleep(PING_INTERVAL)

def is_user_member(user_id, channel):
    resp = requests.get(f"{URL}/getChatMember?chat_id=@{channel}&user_id={user_id}").json()
    print(f"Checking membership for {user_id} in @{channel}: {resp}")
    try:
        return resp["result"]["status"] in ["member", "administrator", "creator"]
    except:
        return False

def check_all_channels(user_id):
    channels = get_force_channels()
    not_joined = []
    for ch in channels:
        if not is_user_member(user_id, ch):
            not_joined.append(ch)
    return not_joined

threading.Thread(target=ping, daemon=True).start()

@app.route("/")
def index():
    return "Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update and "text" in update["message"] and update["message"]["text"].startswith("/start "):
        msg = update["message"]
        cid = msg["chat"]["id"]
        uid = msg["from"]["id"]
        code = msg["text"].split("/start ")[1]

        not_joined = check_all_channels(uid)
        if not_joined:
            buttons = [[{"text": f"عضویت در @{ch}", "url": f"https://t.me/{ch}"}] for ch in not_joined]
            buttons.append([{"text": "عضو شدم ✅", "callback_data": "joined"}])
            send("sendMessage", {
                "chat_id": cid,
                "text": "برای دریافت فایل، ابتدا در کانال‌های زیر عضو شو:",
                "reply_markup": {"inline_keyboard": buttons}
            })
            return "ok"

        file_id = get_file(code)
        if file_id:
            sent = send("sendVideo", {"chat_id": cid, "video": file_id})
            if "result" in sent:
                mid = sent["result"]["message_id"]
                send("sendMessage", {"chat_id": cid, "text": "⚠️این محتوا تا ۲۰ ثانیه دیگر پاک میشود "})
                threading.Timer(20, delete, args=(cid, mid)).start()
        return "ok"

    if "message" in update:
        msg = update["message"]
        uid = msg["from"]["id"]
        cid = msg["chat"]["id"]
        mid = msg["message_id"]
        text = msg.get("text", "")
        state = users.get(uid, {})

        if text == "/start":
            send("sendMessage", {"chat_id": cid, "text": "سلام خوش اومدی عزیزم واسه دریافت فایل مد نظرت از کانال @hottof روی دکمه مشاهده بزن ♥️"})

        elif text == "/panel" and uid in ADMIN_IDS:
            kb = {
                "keyboard": [
                    [{"text": "🔞سوپر"}],
                    [{"text": "🖼پست"}],
                    [{"text": "➕افزودن کانال عضویت"}, {"text": "➖حذف کانال عضویت"}]
                ],
                "resize_keyboard": True
            }
            send("sendMessage", {"chat_id": cid, "text": "سلام آقا مدیر 🔱", "reply_markup": kb})

        elif text == "🔞سوپر" and uid in ADMIN_IDS:
            users[uid] = {"step": "awaiting_multiple_videos", "files": []}
            send("sendMessage", {"chat_id": cid, "text": "چندتا سوپر برام بفرست 🍌 بعدش روی دکمه ادامه بزن", 
                                 "reply_markup": {
                                     "inline_keyboard": [[{"text": "✅ ادامه", "callback_data": "continue_upload"}]]
                                 }})

        elif state.get("step") == "awaiting_multiple_videos" and "video" in msg:
            users[uid]["files"].append(msg["video"]["file_id"])
            send("sendMessage", {
                "chat_id": cid,
                "text": "گرفتم 😏 اگه ویدیوی دیگه‌ای داری بفرست، اگه نه روی «ادامه» بزن",
                "reply_markup": {
                    "inline_keyboard": [[{"text": "✅ ادامه", "callback_data": "continue_upload"}]]
                }
            })

        elif state.get("step") == "awaiting_caption":
            users[uid]["caption"] = text
            users[uid]["step"] = "awaiting_cover"
            send("sendMessage", {"chat_id": cid, "text": "یه عکس برای پیش نمایش بده 📸"})

        elif state.get("step") == "awaiting_cover" and "photo" in msg:
            caption = users[uid]["caption"]
            cover_id = msg["photo"][-1]["file_id"]
            text_out = CHANNEL_TAG
            for file_id in users[uid]["files"]:
                code = gen_code()
                save_file(file_id, code)
                text_out += f"\n<a href='https://t.me/Simhotbot?start={code}'>🎥 مشاهده</a>"
            send("sendPhoto", {
                "chat_id": cid,
                "photo": cover_id,
                "caption": caption + "\n\n" + text_out,
                "parse_mode": "HTML"
            })
            users.pop(uid)
            send("sendMessage", {
                "chat_id": cid,
                "text": "همه چی آماده شد ✅",
                "reply_markup": {
                    "keyboard": [
                        [{"text": "🔞سوپر"}],
                        [{"text": "🖼پست"}],
                        [{"text": "➕افزودن کانال عضویت"}, {"text": "➖حذف کانال عضویت"}]
                    ],
                    "resize_keyboard": True
                }
            })

    if "callback_query" in update:
        query = update["callback_query"]
        uid = query["from"]["id"]
        cid = query["message"]["chat"]["id"]
        mid = query["message"]["message_id"]
        data = query["data"]

        if data == "joined":
    not_joined = check_all_channels(uid)
    if not_joined:
        buttons = [[{"text": f"عضویت در @{ch}", "url": f"https://t.me/{ch}"}] for ch in not_joined]
        buttons.append([{"text": "عضو شدم ✅", "callback_data": "joined"}])
        send("editMessageText", {
            "chat_id": cid,
            "message_id": mid,
            "text": "هنوز عضو همه کانال‌ها نشدی. لطفاً ادامه بده:",
            "reply_markup": {"inline_keyboard": buttons}
        })
    else:
        send("editMessageText", {
            "chat_id": cid,
            "message_id": mid,
            "text": "عالیه! الان دوباره روی لینک ارسال شده کلیک کن تا فایل رو بگیری."
        })
            # (اینجا بدون تغییر می‌مونه)

        elif data == "continue_upload":
            if users.get(uid, {}).get("step") == "awaiting_multiple_videos" and users[uid]["files"]:
                users[uid]["step"] = "awaiting_caption"
                send("editMessageText", {
                    "chat_id": cid,
                    "message_id": mid,
                    "text": "همه ویدیوها ثبت شدن ✅ حالا یه کپشن خوشگل بفرست"
                })
            else:
                send("editMessageText", {
                    "chat_id": cid,
                    "message_id": mid,
                    "text": "هیچ ویدیویی ثبت نشده. اول چند تا بفرست 😅"
                })

        elif state.get("step") == "awaiting_forward" and ("video" in msg or "photo" in msg):
            users[uid]["step"] = "awaiting_post_caption"
            users[uid]["post_msg"] = msg
            send("sendMessage", {"chat_id": cid, "text": "یه کپشن خوشکل بزن حال کنم 😁"})

        elif state.get("step") == "awaiting_post_caption":
            post_msg = users[uid]["post_msg"]
            caption = text + "\n\n" + CHANNEL_TAG
            if "video" in post_msg:
                fid = post_msg["video"]["file_id"]
                send("sendVideo", {"chat_id": cid, "video": fid, "caption": caption})
            else:
                fid = post_msg["photo"][-1]["file_id"]
                send("sendPhoto", {"chat_id": cid, "photo": fid, "caption": caption})
            users[uid]["step"] = "awaiting_forward"
            send("sendMessage", {"chat_id": cid, "text": "بفرما اینم درخواستت ✅️ آماده ام پست بعدی رو بفرستی ارباب🔥"})

        elif text == "➕افزودن کانال عضویت" and uid in ADMIN_IDS:
            users[uid] = {"step": "awaiting_add_channel"}
            send("sendMessage", {"chat_id": cid, "text": "یوزرنیم کانال بدون @ بفرست (مثلاً hottof)"})

        elif state.get("step") == "awaiting_add_channel":
            add_force_channel(text.strip())
            users.pop(uid)
            send("sendMessage", {"chat_id": cid, "text": "کانال با موفقیت اضافه شد ✅"})

        elif text == "➖حذف کانال عضویت" and uid in ADMIN_IDS:
            users[uid] = {"step": "awaiting_remove_channel"}
            send("sendMessage", {"chat_id": cid, "text": "یوزرنیم کانال برای حذف بفرست (بدون @)"})

        elif state.get("step") == "awaiting_remove_channel":
            remove_force_channel(text.strip())
            users.pop(uid)
            send("sendMessage", {"chat_id": cid, "text": "کانال با موفقیت حذف شد ✅"})

    if "callback_query" in update:
        query = update["callback_query"]
        uid = query["from"]["id"]
        cid = query["message"]["chat"]["id"]
        mid = query["message"]["message_id"]
        data = query["data"]

        if data == "joined":
            not_joined = check_all_channels(uid)
            if not_joined:
                buttons = [[{"text": f"عضویت در @{ch}", "url": f"https://t.me/{ch}"}] for ch in not_joined]
                buttons.append([{"text": "عضو شدم ✅", "callback_data": "joined"}])
                send("editMessageText", {
                    "chat_id": cid,
                    "message_id": mid,
                    "text": "هنوز عضو همه کانال‌ها نشدی. لطفاً ادامه بده:",
                    "reply_markup": {"inline_keyboard": buttons}
                })
            else:
                send("editMessageText", {
                    "chat_id": cid,
                    "message_id": mid,
                    "text": "عالیه! الان دوباره روی لینک ارسال شده کلیک کن تا فایل رو بگیری."
                })

    return "ok"

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
