import sqlite3

conn = sqlite3.connect("videos.db", check_same_thread=False)
cur = conn.cursor()

# جدول ذخیره ویدیوها (با ذخیره نام فایل فقط)
cur.execute("""
CREATE TABLE IF NOT EXISTS videos (
    code TEXT PRIMARY KEY,
    file_name TEXT NOT NULL
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
# توابع مربوط به ویدیوها
# --------------------------
def save_file(file_name, code):
    print(f"[DB] Saving file_name: {file_name} with code: {code}")
    with conn:
        conn.execute("INSERT OR REPLACE INTO videos (code, file_name) VALUES (?, ?)", (code, file_name))

def get_file(code):
    print(f"[DB] Getting file for code: {code}")
    row = conn.execute("SELECT file_name FROM videos WHERE code = ?", (code,)).fetchone()
    if row:
        print(f"[DB] Found file_name: {row[0]}")
        return row[0]
    print("[DB] No file found")
    return None

# --------------------------
# توابع مربوط به عضویت اجباری
# --------------------------
def add_force_channel(username):
    username = username.strip().replace("@", "")
    print(f"[DB] Adding force channel: {username}")
    with conn:
        conn.execute("INSERT OR IGNORE INTO force_channels (username) VALUES (?)", (username,))

def remove_force_channel(username):
    username = username.strip().replace("@", "")
    print(f"[DB] Removing force channel: {username}")
    with conn:
        conn.execute("DELETE FROM force_channels WHERE username = ?", (username,))

def get_force_channels():
    rows = conn.execute("SELECT username FROM force_channels").fetchall()
    channels = [row[0] for row in rows]
    print(f"[DB] Current force channels: {channels}")
    return channels
