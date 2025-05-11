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
sent_codes = {}
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

    if "message" in update:
        msg = update["message"]
        uid = msg["from"]["id"]
        cid = msg["chat"]["id"]
        mid = msg["message_id"]
        text = msg.get("text", "")
        state = users.get(uid, {})

        # شروع با کد
        if text.startswith("/start "):
            code = text.split("/start ")[1]
            not_joined = check_all_channels(uid)
            if not_joined:
                users[uid] = {"pending_code": code}
                buttons = [[{"text": f"عضویت در @{ch}", "url": f"https://t.me/{ch}"}] for ch in not_joined]
                buttons.append([{"text": "عضو شدم ✅", "callback_data": "joined"}])
                send("sendMessage", {
                    "chat_id": cid,
                    "text": "برای دریافت فایل، ابتدا در کانال‌های زیر عضو شو:",
                    "reply_markup": {"inline_keyboard": buttons}
                })
                return "ok"

            if sent_codes.get((uid, code)):
                return "ok"

            file_id = get_file(code)
            if file_id:
                sent_codes[(uid, code)] = True
                sent = send("sendVideo", {"chat_id": cid, "video": file_id})
                if "result" in sent:
                    mid = sent["result"]["message_id"]
                    send("sendMessage", {"chat_id": cid, "text": "⚠️این محتوا تا ۲۰ ثانیه دیگر پاک میشود "})
                    threading.Timer(20, delete, args=(cid, mid)).start()
            return "ok"

        # شروع بدون کد
        if text == "/start":
            send("sendMessage", {"chat_id": cid, "text": "سلام خوش اومدی عزیزم واسه دریافت فایل مد نظرت از کانال @hottof روی دکمه مشاهده بزن ♥️"})

        # پنل مدیریت
        elif text == "/panel" and uid in ADMIN_IDS:
            kb = {
                "keyboard": [
                    [{"text": "🔞سوپر"}],
                    [{"text": "🖼پست"}],
                    [{"text": "⚙️عضویت اجباری"}]
                ],
                "resize_keyboard": True
            }
            send("sendMessage", {"chat_id": cid, "text": "سلام آقا مدیر 🔱", "reply_markup": kb})

        elif text == "⚙️عضویت اجباری" and uid in ADMIN_IDS:
            kb = {
                "keyboard": [
                    [{"text": "➕افزودن کانال"}, {"text": "➖حذف کانال"}],
                    [{"text": "📋مشاهده اجباری‌ها"}],
                    [{"text": "🔙برگشت به پنل اصلی"}]
                ],
                "resize_keyboard": True
            }
            send("sendMessage", {"chat_id": cid, "text": "تنظیمات عضویت اجباری:", "reply_markup": kb})

        elif text == "🔙برگشت به پنل اصلی" and uid in ADMIN_IDS:
            send("sendMessage", {
                "chat_id": cid,
                "text": "بازگشت به پنل اصلی ✅️",
                "reply_markup": {
                    "keyboard": [
                        [{"text": "🔞سوپر"}],
                        [{"text": "🖼پست"}],
                        [{"text": "⚙️عضویت اجباری"}]
                    ],
                    "resize_keyboard": True
                }
            })

        elif text == "📋مشاهده اجباری‌ها" and uid in ADMIN_IDS:
            channels = get_force_channels()
            text_out = "لیست کانال‌های اجباری:\n" + "\n".join(["@" + ch for ch in channels]) if channels else "هیچ کانالی تنظیم نشده."
            send("sendMessage", {"chat_id": cid, "text": text_out})

        elif text == "➕افزودن کانال" and uid in ADMIN_IDS:
            users[uid] = {"step": "awaiting_add_channel"}
            send("sendMessage", {"chat_id": cid, "text": "یوزرنیم کانال بدون @ بفرست (مثلاً hottof)"})

        elif state.get("step") == "awaiting_add_channel":
            add_force_channel(text.strip())
            users.pop(uid)
            send("sendMessage", {"chat_id": cid, "text": "کانال با موفقیت اضافه شد ✅"})

        elif text == "➖حذف کانال" and uid in ADMIN_IDS:
            users[uid] = {"step": "awaiting_remove_channel"}
            send("sendMessage", {"chat_id": cid, "text": "یوزرنیم کانال برای حذف بفرست (بدون @)"})

        elif state.get("step") == "awaiting_remove_channel":
            remove_force_channel(text.strip())
            users.pop(uid)
            send("sendMessage", {"chat_id": cid, "text": "کانال با موفقیت حذف شد ✅"})

    # بررسی دکمه «عضو شدم»
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
                code = users.get(uid, {}).get("pending_code")
                if code and not sent_codes.get((uid, code)):
                    file_id = get_file(code)
                    if file_id:
                        sent_codes[(uid, code)] = True
                        send("sendVideo", {"chat_id": cid, "video": file_id})
                send("editMessageText", {
                    "chat_id": cid,
                    "message_id": mid,
                    "text": "عضویت تأیید شد. فایل مدنظر ارسال شد ✅"
                })

    return "ok"

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
