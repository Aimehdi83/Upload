import sqlite3

conn = sqlite3.connect("videos.db", check_same_thread=False)
cur = conn.cursor()

# جدول ذخیره ویدیوها (بدون تغییر)
cur.execute("""
CREATE TABLE IF NOT EXISTS videos (
    code TEXT PRIMARY KEY,
    file_id TEXT NOT NULL
)
""")

# جدول عضویت اجباری (جدید)
cur.execute("""
CREATE TABLE IF NOT EXISTS force_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL
)
""")

conn.commit()

# --------------------------
# توابع مربوط به ویدیوها (دقیقاً مثل قبل)
# --------------------------
def save_file(file_id, code):
    print(f"Saving file_id: {file_id} with code: {code}")  # لاگ ذخیره کردن
    cur.execute("INSERT OR REPLACE INTO videos (code, file_id) VALUES (?, ?)", (code, file_id))
    conn.commit()

def get_file(code):
    print(f"Getting file for code: {code}")  # لاگ دریافت فایل
    cur.execute("SELECT file_id FROM videos WHERE code = ?", (code,))
    row = cur.fetchone()
    if row:
        print(f"Found file_id: {row[0]} for code: {code}")  # لاگ فایل پیدا شده
    else:
        print(f"No file found for code: {code}")  # لاگ اگر هیچ فایلی پیدا نشد
    return row[0] if row else None

# --------------------------
# توابع مربوط به عضویت اجباری (جدید)
# --------------------------
def add_force_channel(username):
    print(f"Adding force channel: {username}")
    cur.execute("INSERT OR IGNORE INTO force_channels (username) VALUES (?)", (username,))
    conn.commit()

def remove_force_channel(username):
    print(f"Removing force channel: {username}")
    cur.execute("DELETE FROM force_channels WHERE username = ?", (username,))
    conn.commit()

def get_force_channels():
    cur.execute("SELECT username FROM force_channels")
    channels = [row[0] for row in cur.fetchall()]
    print(f"Force channels list: {channels}")
    return channels
