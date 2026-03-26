import os
import telebot
import requests
from flask import Flask, request

app = Flask(__name__)

# ==========================================
# 🔐 تنظیمات و متغیرهای محیطی
# ==========================================
TOKEN = os.environ.get('TELEGRAM_TOKEN', '').strip()
URL = os.environ.get('SUPABASE_URL', '').strip()
KEY = os.environ.get('SUPABASE_KEY', '').strip()
ADMIN_ID = os.environ.get('ADMIN_CHAT_ID', '').strip()

bot = telebot.TeleBot(TOKEN, threaded=False)

# هدرهای مورد نیاز برای ارتباط با Supabase REST API
DB_HEADERS = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ==========================================
# 📝 دیکشنری متون (فارسی و انگلیسی)
# ==========================================
STRINGS = {
    'fa': {
        'welcome': "💎 به نُوا VPN خوش آمدید!\nما بهترین کیفیت اینترنت را برای شما فراهم می‌کنیم.",
        'choose_lang': "لطفاً زبان خود را انتخاب کنید:",
        'main_menu': "🏠 منوی اصلی\nموجودی شما: {balance} تومان",
        'btn_buy': "🛒 خرید اشتراک VIP",
        'btn_dash': "👤 داشبورد من",
        'btn_wallet': "💰 کیف پول / شارژ",
        'btn_affiliate': "🤝 کسب درآمد (نمایندگی)",
        'btn_support': "🎧 پشتیبانی",
        'btn_lang': "🌐 Change Language",
        'lang_set': "زبان با موفقیت به فارسی تغییر کرد. 🇮🇷",
        'admin_panel': "🛠 پنل مدیریت فعال شد."
    },
    'en': {
        'welcome': "💎 Welcome to Nova VPN!\nWe provide the best internet quality for you.",
        'choose_lang': "Please select your language:",
        'main_menu': "🏠 Main Menu\nYour Balance: {balance} Tomans",
        'btn_buy': "🛒 Buy VIP Plan",
        'btn_dash': "👤 My Dashboard",
        'btn_wallet': "💰 Wallet / Top-up",
        'btn_affiliate': "🤝 Affiliate Program",
        'btn_support': "🎧 Support",
        'btn_lang': "🌐 تغییر زبان",
        'lang_set': "Language set to English. 🇬🇧",
        'admin_panel': "🛠 Admin Panel Enabled."
    }
}

# ==========================================
# 🛠 توابع کمکی
# ==========================================

def get_user(chat_id):
    """دریافت اطلاعات کاربر از دیتابیس"""
    url = f"{URL}/rest/v1/users?chat_id=eq.{chat_id}&select=*"
    res = requests.get(url, headers=DB_HEADERS)
    data = res.json()
    return data[0] if data else None

def build_main_menu(user):
    """ساخت منوی اصلی بر اساس زبان کاربر"""
    lang = user.get('language', 'fa')
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    s = STRINGS[lang]
    markup.row(s['btn_buy'])
    markup.row(s['btn_dash'], s['btn_wallet'])
    markup.row(s['btn_affiliate'], s['btn_support'])
    markup.row(s['btn_lang'])
    
    # اگر کاربر ادمین بود، دکمه مدیریت هم اضافه شود
    if user.get('role') == 'admin':
        markup.row("🛠 Admin Panel")
        
    return markup

# ==========================================
# 🤖 هندلرهای ربات
# ==========================================

@bot.message_handler(commands=['start'])
def start_cmd(message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    
    if not user:
        # ثبت کاربر جدید
        role = 'admin' if str(chat_id) == ADMIN_ID else 'user'
        new_user = {
            'chat_id': chat_id,
            'username': message.from_user.username,
            'role': role,
            'language': 'fa' # پیش‌فرض
        }
        requests.post(f"{URL}/rest/v1/users", headers=DB_HEADERS, json=new_user)
        
        # نمایش انتخاب زبان برای اولین بار
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(
            telebot.types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa"),
            telebot.types.InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en")
        )
        bot.send_message(chat_id, STRINGS['fa']['welcome'] + "\n\n" + STRINGS['fa']['choose_lang'], reply_markup=markup)
    else:
        # نمایش منوی اصلی
        lang = user.get('language', 'fa')
        bot.send_message(chat_id, STRINGS[lang]['main_menu'].format(balance=user.get('wallet_balance', 0)), reply_markup=build_main_menu(user))

@bot.callback_query_handler(func=lambda call: call.data.startswith('setlang_'))
def callback_lang(call):
    chat_id = call.message.chat.id
    new_lang = call.data.split('_')[1]
    
    # آپدیت زبان در دیتابیس
    requests.patch(f"{URL}/rest/v1/users?chat_id=eq.{chat_id}", headers=DB_HEADERS, json={'language': new_lang})
    
    # نمایش پیام تایید و منوی اصلی
    bot.delete_message(chat_id, call.message.message_id)
    user = get_user(chat_id)
    bot.send_message(chat_id, STRINGS[new_lang]['lang_set'], reply_markup=build_main_menu(user))

@bot.message_handler(func=lambda m: m.text in [STRINGS['fa']['btn_lang'], STRINGS['en']['btn_lang']])
def change_lang_btn(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa"),
        telebot.types.InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en")
    )
    bot.send_message(message.chat.id, "Select Language / انتخاب زبان:", reply_markup=markup)

# ==========================================
# 🌐 تنظیمات Flask و Webhook
# ==========================================

@app.route('/', methods=['GET'])
def index():
    return "✅ Nova VPN Bot is fully operational!"

@app.route('/setup', methods=['GET'])
def setup():
    webhook_url = request.url_root.replace("http://", "https://") + TOKEN
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f"Webhook set to: {webhook_url}"

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'Forbidden', 403
