import os
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# --- Flask Server Setup (Render Port Binding Ke Liye) ---
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is alive and running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

# --- Telegram Bot Logic ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
user_files = {}

# Colorful Keyboard Buttons Function
def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📊 Status / Count", callback_data="status"),
            InlineKeyboardButton("⚡ Merge & Download", callback_data="done_process"),
        ],
        [
            InlineKeyboardButton("🗑 Reset / Clear All", callback_data="reset"),
            InlineKeyboardButton("ℹ️ Help", callback_data="help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_files[user_id] = set()
    
    welcome_text = (
        "👋 **Welcome to Firebase TXT Merger Bot!**\n\n"
        "📂 Mujhe apni `.txt` files bhejte rahiye.\n"
        "✨ Main saare duplicates remove karke ek single file bana dunga.\n\n"
        "Niche diye gaye buttons se control karein 👇"
    )
    
    await update.message.reply_text(
        welcome_text, 
        parse_mode="Markdown", 
        reply_markup=get_main_keyboard()
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    doc = update.message.document

    if not doc.file_name.endswith(".txt"):
        await update.message.reply_text("❌ Kripya sirf `.txt` file hi bhejein.", parse_mode="Markdown")
        return

    if user_id not in user_files:
        user_files[user_id] = set()

    file = await context.bot.get_file(doc.file_id)
    file_bytes = await file.download_as_bytearray()
    
    # Read text lines and remove duplicates
    content = file_bytes.decode("utf-8", errors="ignore")
    count_before = len(user_files[user_id])
    
    for line in content.splitlines():
        cleaned = line.strip()
        if cleaned:
            user_files[user_id].add(cleaned)

    added_lines = len(user_files[user_id]) - count_before

    msg = (
        f"✅ **File Receive Ho Gayi!**\n\n"
        f"➕ New Unique Entries: `{added_lines}`\n"
        f"📈 Total Unique Entries: `{len(user_files[user_id])}`\n\n"
        f"Aur files bhejein ya **Merge & Download** button dabayein."
    )
    
    await update.message.reply_text(
        msg, 
        parse_mode="Markdown", 
        reply_markup=get_main_keyboard()
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in user_files:
        user_files[user_id] = set()

    data = query.data

    if data == "status":
        total = len(user_files[user_id])
        await query.message.reply_text(
            f"📊 **Current Status:**\n\nTotal Unique Entries Saved: `{total}`",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

    elif data == "done_process":
        if not user_files[user_id]:
            await query.message.reply_text(
                "⚠️ Aapne abhi tak koi `.txt` file nahi bheji hai!",
                parse_mode="Markdown"
            )
            return

        output_filename = f"merged_{user_id}.txt"
        with open(output_filename, "w", encoding="utf-8") as f:
            for line in sorted(user_files[user_id]):
                f.write(line + "\n")

        total_count = len(user_files[user_id])
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=open(output_filename, "rb"),
            filename="merged_output.txt",
            caption=f"🎉 **Process Complete!**\n\n🔹 Total Unique Entries: `{total_count}`\n🔥 No Duplicates!",
            parse_mode="Markdown"
        )

        # Cleanup
        if os.path.exists(output_filename):
            os.remove(output_filename)
        user_files[user_id].clear()

    elif data == "reset":
        user_files[user_id].clear()
        await query.message.reply_text(
            "🗑 **Reset Successful!** Purana saara data clear ho gaya hai. Ab nayi files bhej sakte ho.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

    elif data == "help":
        help_text = (
            "ℹ️ **Kaise Use Karein?**\n\n"
            "1️⃣ Bot ko ek ya ek se zyada `.txt` files bhejein.\n"
            "2️⃣ Bot automatic saare duplicates hata kar save kar lega.\n"
            "3️⃣ **⚡ Merge & Download** button par click karke final file lein.\n"
            "4️⃣ Naye sir se start karne ke liye **🗑 Reset** dabayein."
        )
        await query.message.reply_text(
            help_text, 
            parse_mode="Markdown", 
            reply_markup=get_main_keyboard()
        )

if __name__ == "__main__":
    # Flask ko background thread par run karein
    threading.Thread(target=run_flask, daemon=True).start()

    # Telegram bot app start karein
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("Bot with Buttons and Flask server is running...")
    app.run_polling()
