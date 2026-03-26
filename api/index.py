import os
import telebot
import logging
from flask import Flask, request
from supabase import create_client, Client

# ==========================================
# 🔐 تنظیمات متغیرهای محیطی (Environment Variables)
# ==========================================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID')

# راه‌اندازی وب‌سرور (Flask)
app = Flask(__name__)

# بررسی اینکه آیا متغیرها تنظیم شده‌اند یا خیر (برای جلوگیری از خطای 500 در Vercel)
if not TELEGRAM_TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: Environment Variables are missing!")
    bot = None
    supabase = None
else:
    # راه‌اندازی کلاینت دیتابیس (Supabase) و ربات تلگرام
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    bot = telebot.TeleBot(TELEGRAM_TOKEN)
    
    # تنظیم لاگر برای نمایش بهتر خطاها در پنل Vercel
    logger = telebot.logger
    telebot.logger.setLevel(logging.INFO)

# ==========================================
# 🤖 دستورات ربات (Bot Handlers)
# ==========================================

# فقط در صورتی که ربات با موفقیت ساخته شده باشد هندلرها را اضافه می‌کنیم
if bot:
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        chat_id = message.chat.id
        username = message.from_user.username
        
        try:
            # ۱. بررسی اینکه آیا کاربر قبلاً در دیتابیس ثبت شده است یا خیر
            user_data = supabase.table('users').select('*').eq('chat_id', chat_id).execute()
            
            # ۲. اگر کاربر جدید بود، در دیتابیس ذخیره شود
            if not user_data.data:
                # تشخیص خودکار ادمین
                user_role = 'admin' if str(chat_id) == str(ADMIN_CHAT_ID) else 'user'
                
                supabase.table('users').insert({
                    'chat_id': chat_id,
                    'username': username,
                    'language': 'fa',
                    'role': user_role
                }).execute()
            
            # ۳. ارسال پیام خوش‌آمدگویی دوزبانه
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(
                telebot.types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
                telebot.types.InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
            )
            
            welcome_text = (
                "💎 به داشبورد اختصاصی نُوا خوش آمدید!\n"
                "لطفاً زبان خود را انتخاب کنید:\n\n"
                "💎 Welcome to Nova Dashboard!\n"
                "Please select your language:"
            )
            bot.send_message(chat_id, welcome_text, reply_markup=markup)
            
        except Exception as e:
            print(f"Database Error: {e}")
            bot.send_message(chat_id, "❌ خطایی در ارتباط با دیتابیس رخ داد.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
    def handle_language_selection(call):
        chat_id = call.message.chat.id
        selected_lang = call.data.split('_')[1]
        
        try:
            supabase.table('users').update({'language': selected_lang}).eq('chat_id', chat_id).execute()
            
            if selected_lang == 'fa':
                bot.edit_message_text("زبان شما با موفقیت به 🇮🇷 فارسی تنظیم شد. ✅\nبه زودی منوی اصلی برای شما ارسال می‌شود.", chat_id, call.message.message_id)
            else:
                bot.edit_message_text("Your language has been set to 🇬🇧 English. ✅\nThe main menu will be sent shortly.", chat_id, call.message.message_id)
        except Exception as e:
            print(f"Update Error: {e}")

# ==========================================
# 🌐 مسیرهای وب‌سرور (Flask Routes)
# ==========================================

@app.route('/', methods=['GET'])
def index():
    if not bot:
        return "❌ Error: TELEGRAM_TOKEN or SUPABASE Keys are missing in Vercel Environment Variables!", 500
    return "✅ Nova VPN Bot Backend is Running Successfully!"

@app.route('/setup', methods=['GET'])
def setup_webhook():
    if not bot:
        return "❌ Error: Cannot setup webhook because bot is not initialized.", 500
    
    webhook_url = request.url_root.replace("http://", "https://") + TELEGRAM_TOKEN
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f"✅ Webhook successfully set to: {webhook_url}"

# استفاده از مسیر امن و متغیر (اگر توکن نبود از کلمه fallback استفاده می‌شود تا اپلیکیشن کرش نکند)
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

# (در محیط سرورلس Vercel، اپلیکیشن به صورت خودکار توسط متغیر `app` اجرا می‌شود)
