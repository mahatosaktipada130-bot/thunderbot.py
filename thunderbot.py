import logging
import subprocess
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

# States for conversation
WAITING_FOR_PHONE, WAITING_FOR_OTP = range(2)

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Telegram Bot Token
BOT_TOKEN = "8975530287:AAHWIJLTAKR15sX1WJOry_ZGH67UfGKDfWs"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ *Thunder Trail Bot Active!*\n\n"
        "Game chalane ke liye command bhejein:\n"
        "`/run` - Game start karein",
        parse_mode="Markdown"
    )

async def run_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📱 Apna 10-digit mobile number bhejein:")
    return WAITING_FOR_PHONE

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = "".join(filter(str.isdigit, update.message.text))[-10:]
    if len(phone) != 10:
        await update.message.reply_text("❌ Galat number! 10-digit mobile number bhejien:")
        return WAITING_FOR_PHONE

    context.user_data['phone'] = phone
    await update.message.reply_text(f"⏳ Process start ho raha hai for {phone}...")

    # Start the python script as a subprocess
    proc = await asyncio.create_subprocess_exec(
        "python", "thunder_bot.py",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    context.user_data['proc'] = proc

    # Feed phone number to thunder_bot.py
    proc.stdin.write(f"{phone}\n".encode())
    await proc.stdin.drain()

    # Read output until OTP prompt or Login confirmation
    output_log = ""
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        text = line.decode('utf-8', errors='ignore')
        output_log += text
        
        if "OTP:" in text:
            await update.message.reply_text("🔐 OTP aapke phone par aaya hoga. Yahan OTP enter karein:")
            return WAITING_FOR_OTP
        elif "[login] OK" in text or "[done]" in text or "plays_today" in text:
            await update.message.reply_text(f"✅ *Status Update:*\n```{text.strip()}```", parse_mode="Markdown")

    await update.message.reply_text("👍 Script execution complete!")
    return ConversationHandler.END

async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp = update.message.text.strip()
    proc = context.user_data.get('proc')

    if not proc:
        await update.message.reply_text("❌ Process miss ho gaya. Phir se `/run` karein.")
        return ConversationHandler.END

    # Feed OTP to thunder_bot.py
    proc.stdin.write(f"{otp}\n".encode())
    await proc.stdin.drain()

    await update.message.reply_text("⏳ OTP submit kar diya gaya hai, game process ho raha hai...")

    # Read remaining stdout
    stdout, stderr = await proc.communicate()
    output = stdout.decode('utf-8', errors='ignore')

    # Send summary back to Telegram
    clean_lines = [line for line in output.split("\n") if line.startswith(("[play]", "[me]", "[final]", "[done]", "[board]"))]
    summary = "\n".join(clean_lines[-10:]) if clean_lines else output[-1000:]

    await update.message.reply_text(f"🏁 *Game Completed!*\n\n```{summary}```", parse_mode="Markdown")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    proc = context.user_data.get('proc')
    if proc:
        try:
            proc.kill()
        except Exception:
            pass
    await update.message.reply_text("🚫 Operation cancel kar diya gaya.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("run", run_cmd)],
        states={
            WAITING_FOR_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)],
            WAITING_FOR_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_otp)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    print("🤖 Telegram Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
