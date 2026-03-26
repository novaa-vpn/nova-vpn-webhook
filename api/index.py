import os
import telebot
import requests
from flask import Flask, request

app = Flask(__name__)

# بارگذاری متغیرها
TOKEN = os.environ.get('TELEGRAM_TOKEN', '').strip()
URL = os.environ.get('SUPABASE_URL', '').strip()
KEY = os.environ.get('SUPABASE_KEY', '').strip()

bot = telebot.TeleBot(TOKEN, threaded=False) # threaded=False برای محیط سرورلس ضروری است

@bot.message_handler(commands=['start'])
def handle_start(message):
    print(f"📥 دستور Start دریافت شد از: {message.chat.id}")
    try:
        bot.reply_to(message, "✅ Nova VPN Online!\nارتباط با سرور برقرار است.")
        print("📤 پیام پاسخ با موفقیت ارسال شد.")
    except Exception as e:
        print(f"❌ خطا در ارسال پیام تلگرام: {e}")

@app.route('/', methods=['GET'])
def home():
    return f"Bot is running. Token starts with: {TOKEN[:5]}..."

@app.route('/setup', methods=['GET'])
def setup():
    webhook_url = request.url_root.replace("http://", "https://") + TOKEN
    s = bot.set_webhook(url=webhook_url)
    return f"Webhook status: {s} for {webhook_url}"

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    print("🔔 یک پیام جدید از تلگرام رسید!")
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        
        # چاپ محتوای پیام برای دیباگ در لاگ ورسل
        if update.message:
            print(f"📝 متن پیام: {update.message.text}")
            
        bot.process_new_updates([update])
        return '', 200
    return 'Forbidden', 403
