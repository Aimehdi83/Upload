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
    try:
        response = requests.post(f"{URL}/{method}", json=data)
        if response.status_code != 200:
            print(f"Error in sending {method}: {response.status_code}, {response.text}")
            return None
        return response.json()
    except Exception as e:
        print(f"Error in sending {method}: {e}")
        return None

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
    try:
        resp = requests.get(f"{URL}/getChatMember?chat_id=@{channel}&user_id={user_id}").json()
        return resp["result"]["status"] in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Error checking membership for {user_id} in @{channel}: {e}")
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
                    [{"text": "تنظیمات"}]
                ],
                "resize_keyboard": True
            }
            send("sendMessage", {"chat_id": cid, "text": "سلام آقا مدیر 🔱", "reply_markup": kb})

        elif text == "تنظیمات" and uid in ADMIN_IDS:
            kb = {
                "keyboard": [
                    [{"text": "➕افزودن کانال عضویت"}, {"text": "➖حذف کانال عضویت"}],
                    [{"text": "مشاهده عضویت اجباری ها"}, {"text": "بازگشت به منو اصلی"}]
                ],
                "resize_keyboard": True
            }
            send("sendMessage", {"chat_id": cid, "text": "تنظیمات را انتخاب کنید:", "reply_markup": kb})

        elif text == "مشاهده عضویت اجباری ها" and uid in ADMIN_IDS:
            channels = get_force_channels()
            if channels:
                send("sendMessage", {"chat_id": cid, "text": "کانال‌های عضویت اجباری:\n" + "\n".join([f"@{ch}" for ch in channels])})
            else:
                send("sendMessage", {"chat_id": cid, "text": "هیچ کانال عضویت اجباری وجود ندارد."})

        elif text == "بازگشت به منو اصلی" and uid in ADMIN_IDS:
            kb = {
                "keyboard": [
                    [{"text": "🔞سوپر"}],
                    [{"text": "🖼پست"}],
                    [{"text": "تنظیمات"}]
                ],
                "resize_keyboard": True
            }
            send("sendMessage", {"chat_id": cid, "text": "بازگشت به منو اصلی", "reply_markup": kb})

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
                        [{"text": "تنظیمات"}]
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

    return "ok"

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
