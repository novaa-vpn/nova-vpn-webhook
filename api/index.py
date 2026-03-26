import os
import telebot
from flask import Flask, request
from supabase import create_client, Client

# ==========================================
# 🔐 تنظیمات متغیرهای محیطی (Environment Variables)
# ==========================================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID')

# راه‌اندازی کلاینت دیتابیس (Supabase)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# راه‌اندازی ربات تلگرام
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# راه‌اندازی وب‌سرور (Flask) برای دریافت درخواست‌های Vercel
app = Flask(__name__)

# ==========================================
# 🤖 دستورات ربات (Bot Handlers)
# ==========================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    username = message.from_user.username
    
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
    
    # ۳. ارسال پیام خوش‌آمدگویی دوزبانه و انتخاب زبان
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

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def handle_language_selection(call):
    chat_id = call.message.chat.id
    selected_lang = call.data.split('_')[1] # خروجی: fa یا en
    
    # آپدیت کردن زبان در دیتابیس
    supabase.table('users').update({'language': selected_lang}).eq('chat_id', chat_id).execute()
    
    # پاسخ بر اساس زبان انتخابی
    if selected_lang == 'fa':
        bot.edit_message_text("زبان شما با موفقیت به 🇮🇷 فارسی تنظیم شد. ✅\nبه زودی منوی اصلی برای شما ارسال می‌شود.", chat_id, call.message.message_id)
    else:
        bot.edit_message_text("Your language has been set to 🇬🇧 English. ✅\nThe main menu will be sent shortly.", chat_id, call.message.message_id)

# ==========================================
# 🌐 مسیرهای وب‌سرور (Flask Routes)
# ==========================================

@app.route('/', methods=['GET'])
def index():
    return "✅ Nova VPN Bot Backend is Running Successfully!"

# این مسیر بسیار مهم است: برای اتصال تلگرام به Vercel استفاده می‌شود
@app.route('/setup', methods=['GET'])
def setup_webhook():
    # ساخت آدرس وب‌هوک به صورت خودکار با استفاده از آدرس Vercel
    webhook_url = request.url_root.replace("http://", "https://") + TELEGRAM_TOKEN
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f"✅ Webhook successfully set to: {webhook_url}"

# دریافت پیام‌ها از سمت سرورهای تلگرام
@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'Forbidden', 403

# (در محیط سرورلس Vercel، اپلیکیشن به صورت خودکار توسط متغیر `app` اجرا می‌شود)
