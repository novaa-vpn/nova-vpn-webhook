import os
import sys
import traceback
import logging
import requests
from flask import Flask, request

app = Flask(__name__)

# ==========================================
# 🔐 مقداردهی اولیه متغیرها (با حذف فاصله‌های نامرئی)
# ==========================================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '').strip()
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').strip()
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '').strip()
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID', '').strip()

bot = None
startup_error = None

# سیستم ضد-کرش و استفاده از REST API به جای کتابخانه سنگین
try:
    import telebot
    
    if TELEGRAM_TOKEN and SUPABASE_URL and SUPABASE_KEY:
        bot = telebot.TeleBot(TELEGRAM_TOKEN)
        
        logger = telebot.logger
        telebot.logger.setLevel(logging.INFO)
        
        # هدرهای ثابت برای ارتباط مستقیم با دیتابیس سوپابیس
        DB_HEADERS = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

        # ==========================================
        # 🤖 دستورات ربات (Bot Handlers)
        # ==========================================
        @bot.message_handler(commands=['start'])
        def send_welcome(message):
            chat_id = message.chat.id
            username = message.from_user.username
            try:
                # ۱. بررسی اینکه آیا کاربر قبلاً در دیتابیس ثبت شده است یا خیر
                url = f"{SUPABASE_URL}/rest/v1/users?chat_id=eq.{chat_id}&select=*"
                response = requests.get(url, headers=DB_HEADERS)
                user_data = response.json()
                
                # ۲. اگر کاربر جدید بود، در دیتابیس ذخیره شود
                if not user_data: # اگر لیست خالی بود یعنی کاربر جدید است
                    user_role = 'admin' if str(chat_id) == str(ADMIN_CHAT_ID) else 'user'
                    insert_url = f"{SUPABASE_URL}/rest/v1/users"
                    new_user = {
                        'chat_id': chat_id,
                        'username': username,
                        'language': 'fa',
                        'role': user_role
                    }
                    requests.post(insert_url, headers=DB_HEADERS, json=new_user)
                
                # ۳. ارسال پیام خوش‌آمدگویی دوزبانه
                markup = telebot.types.InlineKeyboardMarkup()
                markup.row(
                    telebot.types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
                    telebot.types.InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
                )
                welcome_text = "💎 به داشبورد اختصاصی نُوا خوش آمدید!\nلطفاً زبان خود را انتخاب کنید:\n\n💎 Welcome to Nova Dashboard!\nPlease select your language:"
                bot.send_message(chat_id, welcome_text, reply_markup=markup)
            except Exception as e:
                print(f"Database Error: {e}")
                bot.send_message(chat_id, "❌ خطایی در ارتباط با دیتابیس رخ داد.")

        @bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
        def handle_language_selection(call):
            chat_id = call.message.chat.id
            selected_lang = call.data.split('_')[1]
            try:
                update_url = f"{SUPABASE_URL}/rest/v1/users?chat_id=eq.{chat_id}"
                requests.patch(update_url, headers=DB_HEADERS, json={'language': selected_lang})
                
                if selected_lang == 'fa':
                    bot.edit_message_text("زبان شما با موفقیت به 🇮🇷 فارسی تنظیم شد. ✅\nبه زودی منوی اصلی برای شما ارسال می‌شود.", chat_id, call.message.message_id)
                else:
                    bot.edit_message_text("Your language has been set to 🇬🇧 English. ✅\nThe main menu will be sent shortly.", chat_id, call.message.message_id)
            except Exception as e:
                print(f"Update Error: {e}")

except Exception as e:
    startup_error = traceback.format_exc()
    print(f"Startup Error: {startup_error}")

# ==========================================
# 🌐 مسیرهای وب‌سرور (Flask Routes)
# ==========================================
@app.route('/', methods=['GET'])
def index():
    if startup_error:
        return f"<h1>❌ ارور در راه‌اندازی ربات</h1><pre>{startup_error}</pre>", 500
    if not bot:
        return "❌ Error: متغیرهای محیطی در تنظیمات ورسل وارد نشده‌اند!", 500
    return "✅ Nova VPN Bot Backend is Running Successfully!"

@app.route('/setup', methods=['GET'])
def setup_webhook():
    if startup_error or not bot:
        return "❌ Error: Cannot setup webhook because bot is not initialized. Please visit the root URL (/) to see the error.", 500
    
    webhook_url = request.url_root.replace("http://", "https://") + TELEGRAM_TOKEN
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f"✅ Webhook successfully set to: {webhook_url}"

WEBHOOK_ROUTE = f'/{TELEGRAM_TOKEN}' if TELEGRAM_TOKEN else '/bot-webhook-error'

@app.route(WEBHOOK_ROUTE, methods=['POST'])
def webhook():
    if not bot:
        return 'Bot error', 500
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'Forbidden', 403
