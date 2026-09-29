import os
import re
from bs4 import BeautifulSoup
import flask
from flask import Flask, request
import requests
import telebot

TOKEN = os.environ.get("BOT_TOKEN")  # Render environment variable se token lega
URL = os.environ.get(
    "RENDER_EXTERNAL_URL"
)  # Render ka khud ka URL automatic utha lega

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
session = requests.Session()


@app.route(f"/{TOKEN}", methods=["POST"])
def receive_message():
  json_string = request.get_data().decode("utf-8")
  update = telebot.types.Update.de_json(json_string)
  bot.process_new_updates([update])
  return "!", 200


@app.route("/")
def index():
  return "Bot is running live and fast!", 200


@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
  bot.reply_to(
      message,
      "⚡ **Ultra-Fast Render Bot Active!**\nKisi bhi website ka link bhejein,"
      " main turant forms aur APIs nikal kar dunga.",
  )


@bot.message_handler(func=lambda message: True)
def find_otp_apis(message):
  if not message.text:
    return

  url_match = re.search(r"https?://[^\s]+", message.text)
  if not url_match:
    return

  target_url = url_match.group(0).rstrip(".,;:!?")
  processing_msg = bot.reply_to(
      message, f"⚡ Scanning `{target_url}` instantly..."
  )

  try:
    response = session.get(target_url, headers=HEADERS, timeout=4)
    soup = BeautifulSoup(response.text, "html.parser")

    endpoints = set()
    forms_found = []

    for form in soup.find_all("form"):
      action = form.get("action")
      method = form.get("method", "GET").upper()
      if action:
        forms_found.append(f"• Form [{method}]: `{action}`")

    text_content = response.text
    potential_apis = re.findall(
        r'["\'](/api/v[0-9]/[^"\']+|/[a-zA-Z0-9_/.-]*(?:otp|login|auth|send|verify)[a-zA-Z0-9_/.-]*)["\']',
        text_content,
        re.IGNORECASE,
    )

    for api in potential_apis:
      if len(api) > 3:
        endpoints.add(api)

    report = f"🌐 **Target:** `{target_url}`\n\n"
    if forms_found:
      report += "📋 **Forms Found:**\n" + "\n".join(forms_found[:5]) + "\n\n"
    else:
      report += "📋 **Forms:** No direct forms found.\n\n"

    if endpoints:
      report += "🔗 **Potential APIs:**\n" + "\n".join(
          [f"• `{ep}`" for ep in list(endpoints)[:6]]
      )
    else:
      report += "🔗 **Potential APIs:** None detected."

    bot.edit_message_text(
        report,
        chat_id=message.chat.id,
        message_id=processing_msg.message_id,
        parse_mode="Markdown",
    )

  except Exception as e:
    bot.edit_message_text(
        f"❌ **Error:** `{str(e)}`",
        chat_id=message.chat.id,
        message_id=processing_msg.message_id,
        parse_mode="Markdown",
    )


# Webhook Setup
if __name__ == "__main__":
  bot.remove_webhook()
  if URL:
    bot.set_webhook(url=f"{URL}/{TOKEN}")
  app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
