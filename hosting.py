# ====================================================
#          RUSHERKING  •  PRIME HOSTING v5.2 (FREE & DIRECT)
# ====================================================

import os
import sys
import sqlite3
import subprocess
import time
import random
import string
import threading
import re
import signal
import html as html_mod
from datetime import datetime, timedelta
from telebot import TeleBot, types
from flask import Flask

# ==================== RAILWAY / RENDER CONFIG ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8959750104:AAHw7JF8ZoaCiU3NCGvtoWyDCY9K18YRveI")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 5427735251))
OWNER_NAME = "RUSHERKING"

HOST_DIR = "hosted_files"
MAX_LOG_SIZE_MB = 5

DEFAULT_EMOJI = {
    "fire": "5424972470023104089",
    "star": "5438496463044752972",
    "check": "5206607081334906820",
    "cross": "5210952531676504517",
    "bell": "5458603043203327669",
    "money": "5409048419211682843",
    "lock": "5296369303661067030",
    "warning": "5447644880824181073",
    "settings": "5341715473882955310",
    "gift": "5309849913218071967",
    "rocket": "5188481279963715781",
    "diamond": "5199448307155350272",
    "wave": "5870734657384877785",
    "user": "5879770735999717115",
    "people": "5942877472163892475",
    "bot": "5931415565955503486",
    "link": "5271604874419647061",
    "refresh": "5375338737028841420",
    "top": "5415655814079723871",
    "card": "5927169041595634481",
    "support": "5884510167986343350",
    "urgent": "5224607267797606837",
    "crown": "5438496463044752972",
    "spark": "5424972470023104089",
}

config = {
    "bot_username": "",
    "admin_username": "",
    "channel_username": "",
    "force_channel": "",
    "brand_name": "PRIME HOSTING SERVER",
    "free_limit": 50,
    "prime_limit": 50,
}
EMOJI_IDS = dict(DEFAULT_EMOJI)

os.makedirs(HOST_DIR, exist_ok=True)
bot = TeleBot(BOT_TOKEN, threaded=True, num_threads=50)
waiting_states = {}

# ==================== RENDER KEEP-ALIVE SERVER ====================
app = Flask('')

@app.route('/')
def home():
    return "Bot is active and running smoothly!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()

# ==================== DATABASE ====================
def get_db():
    conn = sqlite3.connect("hosting_data.db", check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            is_prime INTEGER DEFAULT 1,
            prime_expire TEXT DEFAULT NULL,
            referred_by INTEGER DEFAULT NULL,
            referral_count INTEGER DEFAULT 0,
            ref_pending INTEGER DEFAULT NULL,
            joined_ok INTEGER DEFAULT 1
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hosted_bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            filename TEXT,
            filepath TEXT,
            logpath TEXT,
            pid INTEGER DEFAULT NULL,
            status TEXT DEFAULT 'stopped',
            auto_guard INTEGER DEFAULT 1,
            speed_boost INTEGER DEFAULT 0,
            created_at TEXT DEFAULT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prime_codes (
            code TEXT PRIMARY KEY,
            days INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    default_config = {
        "bot_username": "",
        "admin_username": "",
        "channel_username": "",
        "force_channel": "",
        "brand_name": "PRIME HOSTING SERVER",
        "free_limit": "50",
        "prime_limit": "50",
    }
    for k, v in default_config.items():
        cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)", (k, v))
    for ek, ev in DEFAULT_EMOJI.items():
        cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)", (f"emoji_{ek}", ev))
    conn.commit()
    conn.close()

init_db()

def load_config():
    global config, EMOJI_IDS
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM config")
    rows = cursor.fetchall()
    conn.close()
    emoji_map = dict(DEFAULT_EMOJI)
    for row in rows:
        key = row['key']
        val = row['value']
        if key in config:
            if key in ["free_limit", "prime_limit"]:
                try:
                    config[key] = int(val)
                except Exception:
                    pass
            else:
                config[key] = val
        elif key.startswith("emoji_"):
            ek = key[6:]
            if val and str(val).isdigit():
                emoji_map[ek] = str(val)
    EMOJI_IDS = emoji_map

load_config()

def ce(emoji_id: str, fallback: str) -> str:
    if emoji_id and str(emoji_id).isdigit():
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback

def pe(key: str, fallback: str) -> str:
    eid = EMOJI_IDS.get(key) or DEFAULT_EMOJI.get(key)
    return ce(str(eid), fallback) if eid else fallback

def brand() -> str:
    return config.get("brand_name") or "PRIME HOSTING SERVER"

def set_config_value(key: str, value: str):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()
    load_config()

# ==================== HELPERS ====================
def register_user(user_id, ref_by=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, is_prime, joined_ok) VALUES (?, 1, 1)", (user_id,))
        conn.commit()
    conn.close()

def send_typing(chat_id):
    try:
        bot.send_chat_action(chat_id, 'typing')
    except Exception:
        pass

def send_or_edit(chat_id, text, reply_markup=None, message_id=None, parse_mode="HTML"):
    send_typing(chat_id)
    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, parse_mode=parse_mode, reply_markup=reply_markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)

def is_process_alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def safe_popen(filepath, logpath):
    log_file = open(logpath, 'a', encoding='utf-8')
    log_file.write(f"\n--- [STARTED {datetime.now()}] ---\n")
    log_file.flush()
    cmd = [sys.executable, "-u", filepath]
    cwd = os.path.dirname(filepath) or "."
    try:
        proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, cwd=cwd, start_new_session=True)
    except Exception:
        try:
            log_file.close()
        except Exception:
            pass
        log_file = open(logpath, 'a', encoding='utf-8')
        proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, cwd=cwd)
    return proc

def safe_kill(pid):
    if not pid or not is_process_alive(pid):
        return
    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
        time.sleep(0.3)
        if is_process_alive(pid):
            os.killpg(os.getpgid(pid), signal.SIGKILL)
    except Exception:
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.3)
            if is_process_alive(pid):
                os.kill(pid, 9)
        except Exception:
            try:
                os.kill(pid, 9)
            except Exception:
                pass

# ==================== AUTO LIBRARY INSTALLER ====================
def extract_imports(filepath):
    packages = set()
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        for match in re.finditer(r'^\s*(?:from|import)\s+([a-zA-Z0-9_\.]+)', content, re.MULTILINE):
            pkg = match.group(1).split('.')[0]
            stdlib = {
                'os', 'sys', 'time', 'datetime', 'json', 're', 'math', 'random',
                'string', 'threading', 'subprocess', 'sqlite3', 'logging',
                'collections', 'functools', 'itertools', 'pathlib', 'shutil',
                'tempfile', 'urllib', 'http', 'socket', 'ssl', 'hashlib',
                'base64', 'pickle', 'copy', 'traceback', 'typing', 'dataclasses',
                'enum', 'abc', 'io', 'csv', 'xml', 'html', 'email', 'asyncio', 'queue', 'signal'
            }
            if pkg and pkg not in stdlib and not pkg.startswith('_'):
                packages.add(pkg)
    except Exception:
        pass
    return packages

def auto_install_packages(filepath, logpath):
    packages = extract_imports(filepath)
    if not packages:
        return [], []
    installed = []
    failed = []
    name_map = {
        'telebot': 'pyTelegramBotAPI', 'telegram': 'python-telegram-bot',
        'PIL': 'Pillow', 'cv2': 'opencv-python', 'bs4': 'beautifulsoup4',
        'yaml': 'PyYAML', 'dotenv': 'python-dotenv', 'requests': 'requests',
        'aiohttp': 'aiohttp', 'flask': 'flask', 'fastapi': 'fastapi',
        'uvicorn': 'uvicorn', 'numpy': 'numpy', 'pandas': 'pandas', 'yt_dlp': 'yt-dlp',
    }
    with open(logpath, 'a', encoding='utf-8') as log:
        log.write(f"\n--- [AUTO-PIP START {datetime.now()}] ---\n")
        for pkg in packages:
            pip_name = name_map.get(pkg, pkg)
            try:
                result = subprocess.run([sys.executable, "-m", "pip", "show", pip_name], capture_output=True, text=True, timeout=15)
                if result.returncode == 0:
                    continue
                install = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--no-cache-dir", pip_name], capture_output=True, text=True, timeout=120)
                if install.returncode == 0:
                    installed.append(pip_name)
                else:
                    failed.append(pip_name)
            except Exception:
                failed.append(pip_name)
    return installed, failed

# ==================== CRASH GUARD ====================
def crash_guard_worker():
    while True:
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM hosted_bots WHERE status = 'running'")
            running_bots = cursor.fetchall()
            for b in running_bots:
                pid = b['pid']
                bot_id = b['id']
                filepath = b['filepath']
                logpath = b['logpath']
                if not is_process_alive(pid) if pid else True:
                    try:
                        proc = safe_popen(filepath, logpath)
                        cursor.execute("UPDATE hosted_bots SET pid = ? WHERE id = ?", (proc.pid, bot_id))
                        conn.commit()
                    except Exception:
                        cursor.execute("UPDATE hosted_bots SET status = 'stopped', pid = NULL WHERE id = ?", (bot_id,))
                        conn.commit()
            conn.close()
        except Exception:
            pass
        time.sleep(8)

threading.Thread(target=crash_guard_worker, daemon=True).start()

# ==================== STYLES & BUTTONS ====================
def _btn_to_dict_patch(original_to_dict):
    def patched(self):
        d = original_to_dict(self)
        style = getattr(self, "_style", None)
        icon = getattr(self, "_icon_custom_emoji_id", None)
        if style: d["style"] = style
        if icon: d["icon_custom_emoji_id"] = str(icon)
        return d
    return patched

if not getattr(types.InlineKeyboardButton, "_style_patched", False):
    types.InlineKeyboardButton.to_dict = _btn_to_dict_patch(types.InlineKeyboardButton.to_dict)
    types.InlineKeyboardButton._style_patched = True
if not getattr(types.KeyboardButton, "_style_patched", False):
    types.KeyboardButton.to_dict = _btn_to_dict_patch(types.KeyboardButton.to_dict)
    types.KeyboardButton._style_patched = True

def ibtn(text, callback_data=None, url=None, style=None, icon=None):
    kwargs = {}
    if callback_data: kwargs["callback_data"] = callback_data
    if url: kwargs["url"] = url
    btn = types.InlineKeyboardButton(text, **kwargs)
    if style: btn._style = style
    eid = EMOJI_IDS.get(icon) if icon else None
    if eid: btn._icon_custom_emoji_id = str(eid)
    return btn

def kbtn(text, style=None, icon=None):
    btn = types.KeyboardButton(text)
    if style: btn._style = style
    eid = EMOJI_IDS.get(icon) if icon else None
    if eid: btn._icon_custom_emoji_id = str(eid)
    return btn

def main_reply_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True, row_width=2)
    markup.row(kbtn("Upload Bot", style="primary", icon="rocket"), kbtn("My Bots", style="primary", icon="bot"))
    markup.row(kbtn("PRIME ZONE", style="danger", icon="diamond"))
    markup.row(kbtn("Status", style="primary", icon="refresh"), kbtn("Help", style="primary", icon="bell"))
    ch = config.get("channel_username", "").strip()
    ad = config.get("admin_username", "").strip()
    extra = []
    if ch: extra.append(kbtn("Channel", style="primary", icon="link"))
    if ad: extra.append(kbtn("Support", style="danger", icon="support"))
    if extra: markup.row(*extra)
    if user_id == ADMIN_ID:
        markup.row(kbtn("Admin Panel", style="danger", icon="settings"))
    return markup

def now_ist_str():
    try:
        from datetime import timezone, timedelta
        ist = timezone(timedelta(hours=5, minutes=30))
        return datetime.now(ist).strftime("%d-%m-%Y %I:%M:%S %p IST")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " IST"

# ==================== COMMANDS ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    register_user(user_id)
    user_name = message.from_user.first_name or "User"
    
    welcome = (
        f'{pe("spark", "✨")} <b>{brand()}</b> {pe("spark", "✨")}\n'
        f'{pe("crown", "👑")} <b>{OWNER_NAME}</b> • v5.2\n'
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f'{pe("wave", "👋")} Welcome, <b>{user_name}</b>!\n\n'
        f'{pe("card", "🪪")} <b>Profile</b>\n'
        f'├ {pe("user", "🏷")} Name: <code>{user_name}</code>\n'
        f'├ {pe("card", "🆔")} ID: <code>{user_id}</code>\n'
        f'└ {pe("diamond", "💎")} Status: 👑 <b>UNLIMITED FREE VIP</b>\n\n'
        f'{pe("rocket", "⚡")} <b>Hosting</b>\n'
        f'├ {pe("bot", "📦")} Limit: <code>50</code> bots\n'
        f'└ {pe("lock", "🛡")} Crash Guard: 24/7 Active\n\n'
        f'━━━━━━━━━━━━━━━━━━━━\n'
        f'{pe("top", "👇")} Use buttons below:'
    )
    bot.send_message(message.chat.id, welcome, parse_mode="HTML", reply_markup=main_reply_keyboard(user_id))

@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = message.from_user.id
    send_typing(message.chat.id)
    register_user(user_id)

    if not message.document.file_name or not message.document.file_name.lower().endswith('.py'):
        bot.reply_to(message, "❌ Only `.py` Python files are allowed.")
        return

    filename = message.document.file_name
    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)

    user_dir = os.path.join(os.getcwd(), HOST_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    filepath = os.path.join(user_dir, filename)
    logpath = filepath + ".log"

    with open(filepath, 'wb') as f:
        f.write(downloaded)

    with open(logpath, 'w', encoding='utf-8') as f:
        f.write(f"--- [UPLOADED {datetime.now()}] Ready to start ---\n")

    conn = get_db()
    cursor = conn.cursor()
    now_str = now_ist_str()
    cursor.execute(
        "INSERT INTO hosted_bots (user_id, filename, filepath, logpath, status, created_at) VALUES (?, ?, ?, ?, 'stopped', ?)",
        (user_id, filename, filepath, logpath, now_str)
    )
    conn.commit()
    conn.close()

    auto_install_packages(filepath, logpath)

    bot.reply_to(
        message,
        f'{pe("check", "✅")} <code>{html_mod.escape(filename)}</code> uploaded successfully & directly ready!\n\n'
        f'📱 Go to <b>My Bots</b> to Start your bot.',
        parse_mode="HTML",
    )

@bot.message_handler(func=lambda m: m.text in {
    "Upload Bot", "My Bots", "PRIME ZONE", "Status", "Help", "Channel", "Support", "Admin Panel"
})
def bottom_menu_handler(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text.strip()
    send_typing(chat_id)
    register_user(user_id)

    if text == "Upload Bot":
        bot.send_message(chat_id, f'{pe("rocket", "📥")} Send your <code>.py</code> file here. It will be hosted instantly!', parse_mode="HTML", reply_markup=main_reply_keyboard(user_id))
    elif text == "My Bots":
        _show_my_bots(chat_id, user_id)
    elif text == "PRIME ZONE":
        msg = (
            f'{pe("diamond", "💎")} <b>PRIME ZONE (FREE FOR ALL)</b>\n'
            f'{pe("crown", "👑")} <b>{OWNER_NAME}</b>\n'
            f'━━━━━━━━━━━━━━━━━━━━\n'
            f'Status: 👑 <b>VIP UNLIMITED</b>\n\n'
            f'{pe("fire", "🔥")} All premium features are unlocked completely free!'
        )
        bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=main_reply_keyboard(user_id))
    elif text == "Status":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM hosted_bots")
        total = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as running FROM hosted_bots WHERE status='running'")
        running = cursor.fetchone()['running']
        conn.close()
        msg = (
            f'{pe("settings", "🖥️")} <b>Server Status</b>\n'
            f'━━━━━━━━━━━━━━━━━━━━\n'
            f'{pe("bot", "🤖")} Hosted Bots: <code>{total}</code>\n'
            f'{pe("check", "🟢")} Running: <code>{running}</code>'
        )
        bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=main_reply_keyboard(user_id))
    elif text == "Help":
        msg = f'{pe("bell", "❓")} <b>Help Guide</b>\nUpload any `.py` script, go to *My Bots*, and click **Start**!'
        bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=main_reply_keyboard(user_id))
    elif text == "Channel":
        ch = config.get("channel_username", "").strip()
        if ch: bot.send_message(chat_id, f"📢 Channel: https://t.me/{ch}")
    elif text == "Support":
        ad = config.get("admin_username", "").strip()
        if ad: bot.send_message(chat_id, f"📞 Support: https://t.me/{ad}")
    elif text == "Admin Panel":
        if user_id != ADMIN_ID: return
        bot.send_message(chat_id, "⚙️ Admin Panel Active", reply_markup=main_reply_keyboard(user_id))

def _show_my_bots(chat_id, user_id, msg_id=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hosted_bots WHERE user_id = ? ORDER BY id DESC", (user_id,))
    bots = cursor.fetchall()
    conn.close()
    if not bots:
        bot.send_message(chat_id, f'{pe("cross", "❌")} No bots found.', parse_mode="HTML", reply_markup=main_reply_keyboard(user_id))
        return
    markup = types.InlineKeyboardMarkup()
    for b in bots:
        alive = b['status'] == 'running' and b['pid'] and is_process_alive(b['pid'])
        icon = "🟢" if alive else "🔴"
        label = f"{icon} {b['filename']}"
        markup.add(ibtn(label[:40], callback_data=f"manage_{b['id']}", style="primary", icon="bot"))
    markup.add(ibtn("Main Menu", callback_data="main_menu", style="danger", icon="top"))
    send_or_edit(chat_id, "⚙️ *Your Bots:*", markup, msg_id)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    user_id = call.from_user.id
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    data = call.data
    send_typing(chat_id)

    if data == "main_menu":
        try:
            bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
        bot.send_message(chat_id, f'{pe("top", "🏠")} <b>Main Menu</b>', parse_mode="HTML", reply_markup=main_reply_keyboard(user_id))
    elif data == "my_bots":
        _show_my_bots(chat_id, user_id, msg_id)
    elif data.startswith("manage_"):
        bot_id = int(data.split("_")[1])
        render_bot_control(chat_id, bot_id, msg_id, user_id)
    elif data.startswith("startbot_"):
        bot_id = int(data.split("_")[1])
        start_bot_action(chat_id, bot_id, msg_id, user_id)
    elif data.startswith("stopbot_"):
        bot_id = int(data.split("_")[1])
        stop_bot_action(chat_id, bot_id, msg_id, user_id)
    elif data.startswith("logbot_"):
        bot_id = int(data.split("_")[1])
        show_logs_action(chat_id, bot_id, msg_id)
    elif data.startswith("clearlog_"):
        bot_id = int(data.split("_")[1])
        clear_logs_action(chat_id, bot_id, msg_id)
    elif data.startswith("piplist_"):
        bot_id = int(data.split("_")[1])
        show_pip_action(chat_id, bot_id, msg_id)
    elif data.startswith("delbot_"):
        bot_id = int(data.split("_")[1])
        delete_bot_action(chat_id, bot_id, msg_id, user_id)

def render_bot_control(chat_id, bot_id, msg_id=None, user_id=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hosted_bots WHERE id = ?", (bot_id,))
    b = cursor.fetchone()
    conn.close()

    if not b:
        bot.send_message(chat_id, "❌ Bot not found.")
        return

    if user_id and user_id != ADMIN_ID and b['user_id'] != user_id:
        bot.send_message(chat_id, "❌ Access denied.")
        return

    alive = b['status'] == 'running' and b['pid'] and is_process_alive(b['pid'])
    status = "🟢 Running" if alive else "🔴 Stopped"

    msg = (
        f"🤖 *Bot Control*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📄 File: `{b['filename']}`\n"
        f"📊 Status: {status}\n"
        f"🆔 PID: `{b['pid'] if alive else 'N/A'}`"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    if alive:
        markup.add(ibtn("Stop", callback_data=f"stopbot_{b['id']}", style="danger", icon="cross"))
    else:
        markup.add(ibtn("Start", callback_data=f"startbot_{b['id']}", style="primary", icon="rocket"))
    markup.add(
        ibtn("Logs", callback_data=f"logbot_{b['id']}", style="primary", icon="bell"),
        ibtn("Clear Logs", callback_data=f"clearlog_{b['id']}", style="danger", icon="warning"),
    )
    markup.add(
        ibtn("Packages", callback_data=f"piplist_{b['id']}", style="primary", icon="card"),
        ibtn("Refresh", callback_data=f"manage_{b['id']}", style="primary", icon="refresh"),
    )
    markup.add(ibtn("Delete", callback_data=f"delbot_{b['id']}", style="danger", icon="cross"))
    markup.add(ibtn("My Bots", callback_data="my_bots", style="danger", icon="bot"))
    send_or_edit(chat_id, msg, markup, msg_id)

def start_bot_action(chat_id, bot_id, msg_id, user_id=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hosted_bots WHERE id = ?", (bot_id,))
    b = cursor.fetchone()
    if not b:
        conn.close()
        return

    if not b['pid'] or not is_process_alive(b['pid']):
        try:
            process = safe_popen(b['filepath'], b['logpath'])
            cursor.execute("UPDATE hosted_bots SET status = 'running', pid = ? WHERE id = ?", (process.pid, bot_id))
            conn.commit()
        except Exception:
            pass
    conn.close()
    render_bot_control(chat_id, bot_id, msg_id, user_id)

def stop_bot_action(chat_id, bot_id, msg_id, user_id=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hosted_bots WHERE id = ?", (bot_id,))
    b = cursor.fetchone()
    if not b:
        conn.close()
        return

    if b['pid']:
        safe_kill(b['pid'])

    cursor.execute("UPDATE hosted_bots SET status = 'stopped', pid = NULL WHERE id = ?", (bot_id,))
    conn.commit()
    conn.close()
    render_bot_control(chat_id, bot_id, msg_id, user_id)

def show_logs_action(chat_id, bot_id, msg_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hosted_bots WHERE id = ?", (bot_id,))
    b = cursor.fetchone()
    conn.close()

    if not b or not os.path.exists(b['logpath']):
        bot.send_message(chat_id, "❌ Log file not found.")
        return

    try:
        with open(b['logpath'], 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        last = "".join(lines[-40:]).strip() or "No logs yet."
        if len(last) > 3500: last = last[-3500:]
        msg = f"📜 *Logs* — `{b['filename']}`\n```\n{last}\n```"
        markup = types.InlineKeyboardMarkup()
        markup.add(ibtn("Refresh", callback_data=f"logbot_{bot_id}", style="primary", icon="refresh"), ibtn("Back", callback_data=f"manage_{bot_id}", style="danger", icon="top"))
        send_or_edit(chat_id, msg, markup, msg_id)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: `{str(e)}`")

def clear_logs_action(chat_id, bot_id, msg_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT logpath FROM hosted_bots WHERE id = ?", (bot_id,))
    b = cursor.fetchone()
    conn.close()
    if b and os.path.exists(b['logpath']):
        try:
            with open(b['logpath'], 'w', encoding='utf-8') as f:
                f.write(f"--- [LOGS CLEARED {datetime.now()}] ---\n")
        except Exception:
            pass
    show_logs_action(chat_id, bot_id, msg_id)

def show_pip_action(chat_id, bot_id, msg_id):
    try:
        res = subprocess.run([sys.executable, "-m", "pip", "list", "--format=columns"], capture_output=True, text=True, timeout=20)
        packages = res.stdout[:2800] if res.stdout else "No packages."
        msg = f"📋 *Installed Packages*\n```\n{packages}\n```"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data=f"manage_{bot_id}"))
        send_or_edit(chat_id, msg, markup, msg_id)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: `{str(e)}`")

def delete_bot_action(chat_id, bot_id, msg_id, user_id=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hosted_bots WHERE id = ?", (bot_id,))
    b = cursor.fetchone()
    if not b:
        conn.close()
        return

    if b['pid']: safe_kill(b['pid'])
    for path in [b['filepath'], b['logpath']]:
        if path and os.path.exists(path):
            try: os.remove(path)
            except Exception: pass

    cursor.execute("DELETE FROM hosted_bots WHERE id = ?", (bot_id,))
    conn.commit()
    conn.close()

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 My Bots", callback_data="my_bots"))
    send_or_edit(chat_id, "🗑️ Bot & logs deleted.", markup, msg_id)

# ==================== START ====================
if __name__ == '__main__':
    print(f"👑 {OWNER_NAME}")
    print(f"⚡ {brand()} v5.2 (Free & Direct Mode)")
    print(f"✅ Admin ID: {ADMIN_ID}")
    
    # Render web server start karein taaki app sleep na kare
    keep_alive()
    
    # Telegram bot infinity polling start karein
    bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=10)
