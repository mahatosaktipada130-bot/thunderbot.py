#😎 Tᴇʀᴇ Lɪʏᴇ Hɪ Cʀᴇᴅɪᴛ Cʜʜᴏʀ Dɪʏᴀ Hᴀɪ ❤️‍🔥
import os, time, json, threading
from datetime import datetime
import blackboxprotobuf
import requests, urllib3
from flask import Flask, request, jsonify
import telebot

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
app = Flask(__name__)

# --- TELEGRAM BOT CONFIGURATION ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE") 
bot = telebot.TeleBot(BOT_TOKEN)

# --- REVERSED VALUES & DECODER ---
def _x(v):
    r = ""
    for i in range(len(v) - 1, -1, -1):
        r += v[i]
    return r

_URL     = _x("ahcaGesahcruP/moc.elibomerifeerf.dni.tneilc//:sptth")
_PAYLOAD = _x("238A47DFD511C8B27872C2CAAD9B021D")
_VER     = _x("55BO")
_OUT     = _x("nosj.tluser")
_IMG     = _x("segami_meti")
_JWT     = _x("}{=drowssap&}{=diu?nekot/cilbup/ipa/ppa.elbavol.twjxraswak//:sptth")
_FFITEM  = _x("}{/smeti/gro.xbuhved.smetiff//:sptth")
_UA      = "UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)"

_OWN = {
    "owner":        _x("tfird_gd/em.t"),
    "main_channel": _x("TFIRDGD/em.t"),
    "likes_group":  _x("fftfirdgd/em.t"),
}

def jwt(uid, pw):
    try:
        r = requests.get(_JWT.format(uid, pw), timeout=15)
        d = r.json()
        return d.get("token") or d.get("jwt") or d.get("jwt_token"), None
    except Exception as e:
        return None, str(e)

def ids(data):
    s = set()
    def go(o):
        if isinstance(o, dict):
            for v in o.values():
                if isinstance(v, (int, str)) and str(v).strip().isdigit() and len(str(v).strip()) >= 6:
                    s.add(str(v).strip())
                go(v)
        elif isinstance(o, list):
            [go(i) for i in o]
    go(data)
    return list(s)

def imgs(data):
    out = []
    os.makedirs(_IMG, exist_ok=True)
    for i in ids(data):
        url = _FFITEM.format(i)
        p = os.path.join(_IMG, f"{i}.png")
        if os.path.exists(p):
            out.append({"item_id": i, "url": url, "status": "cached"}); continue
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200 and len(r.content) > 100:
                open(p, "wb").write(r.content)
                out.append({"item_id": i, "url": url, "status": "downloaded"})
            else:
                out.append({"item_id": i, "url": url, "status": "failed"})
        except Exception as e:
            out.append({"item_id": i, "url": url, "status": str(e)})
        time.sleep(0.3)
    return out

def save(uid, tok, data, hex_):
    a = []
    if os.path.exists(_OUT):
        try: a = json.load(open(_OUT)) or []
        except: a = []
    a.append({"uid": uid, "token": tok, "spin_number": 1,
              "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
              "raw_hex": hex_, "reward_data": data})
    json.dump(a, open(_OUT, "w"), indent=4,
              default=lambda b: b.hex() if isinstance(b, bytes) else str(b))

def spin(tok, uid):
    h = {"Authorization": f"Bearer {tok}", "X-GA": "v1 1", "ReleaseVersion": _VER,
         "Content-Type": "application/octet-stream", "User-Agent": _UA}
    try:
        r = requests.post(_URL, data=bytes.fromhex(_PAYLOAD), headers=h, verify=False, timeout=15)
    except Exception as e:
        return {"success": False, "error": str(e), **_OWN}
    if r.status_code != 200:
        return {"success": False, "status_code": r.status_code, "error": r.text, **_OWN}
    try: data, _ = blackboxprotobuf.decode_message(r.content)
    except Exception as e: data = {"err": str(e)}
    hex_ = r.content.hex().upper()
    im = imgs(data)
    save(uid, tok, data, hex_)
    return {"success": True, "uid": uid, "raw_hex": hex_, "reward_data": data,
            "item_images": im, "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
            **_OWN}

# --- FLASK ENDPOINTS ---
@app.route("/naruto-spin")
def ns():
    uid, pw = request.args.get("uid"), request.args.get("pass")
    if not uid or not pw:
        return jsonify({"success": False, "error": "Use: /naruto-spin?uid={}&pass={}", **_OWN}), 400
    tok, err = jwt(uid, pw)
    if not tok:
        return jsonify({"success": False, "uid": uid, "error": err, **_OWN}), 401
    r = spin(tok, uid)
    r["token"] = tok
    return jsonify(r), 200 if r.get("success") else 500

@app.route("/")
def home():
    return jsonify({"status": "Server and Bot Running Live!", **_OWN})

# --- TELEGRAM BOT HANDLERS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "⚡ **Naruto Spinner Bot Active!**\n\nUsage:\n`/spin <UID> <PASSWORD>`", parse_mode="Markdown")

@bot.message_handler(commands=['spin'])
def run_spin_cmd(message):
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "❌ **Incorrect Format!**\nUse: `/spin <UID> <PASSWORD>`", parse_mode="Markdown")
        return
    
    uid, pw = args[1], args[2]
    bot.reply_to(message, "⏳ Processing request...")
    
    tok, err = jwt(uid, pw)
    if not tok:
        bot.reply_to(message, f"❌ **Login Failed:** {err or 'Invalid Credentials'}")
        return
        
    res = spin(tok, uid)
    if res.get("success"):
        msg = f"✅ **Spin Successful!**\n\n🆔 **UID:** `{uid}`\n⏰ **Time:** {res.get('timestamp')}\n📦 **Hex:** `{res.get('raw_hex')[:30]}...`"
        bot.reply_to(message, msg, parse_mode="Markdown")
    else:
        bot.reply_to(message, f"❌ **Error:** {res.get('error', 'Unknown Error')}")

# --- BACKGROUND THREADS ---
def start_bot():
    while True:
        try:
            print("Starting Bot Polling...")
            bot.polling(non_stop=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Bot Polling Error: {e}")
            time.sleep(5)

def keep_alive():
    # Render URL ko ping karke inactive hone se bachata hai
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        return
    while True:
        time.sleep(600)  # Har 10 minute me ping karega
        try:
            requests.get(url, timeout=10)
            print("Self-ping successful!")
        except Exception as e:
            print(f"Self-ping failed: {e}")

# Threads ko global level par start kiya taaki Gunicorn ke under chal sake
threading.Thread(target=start_bot, daemon=True).start()
threading.Thread(target=keep_alive, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
