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
# 📝 دیکشنری متون (دوزبانه)
# ==========================================
STRINGS = {
    'fa': {
        'welcome': "💎 به نُوا VPN خوش آمدید!",
        'choose_lang': "لطفاً زبان خود را انتخاب کنید:",
        'main_menu': "🏠 منوی اصلی\n➖➖➖➖➖➖\n💰 موجودی: {balance} تومان\n👥 زیرمجموعه: {ref_count} نفر",
        'btn_buy': "🛒 خرید اشتراک VIP",
        'btn_dash': "👤 داشبورد من",
        'btn_wallet': "💰 کیف پول / شارژ",
        'btn_affiliate': "🤝 کسب درآمد",
        'btn_support': "🎧 پشتیبانی",
        'btn_lang': "🌐 Change Language",
        'dash_title': "👤 **پنل کاربری شما**\n\n🆔 آیدی: `{chat_id}`\n💰 اعتبار: {balance} تومان\n📅 عضویت: {date}\n\n📦 **سرویس‌های فعال شما:**\n{services}",
        'no_services': "❌ شما هنوز اشتراک فعالی ندارید.",
        'affiliate_title': "🤝 **سیستم کسب درآمد نُوا**\n\nبا دعوت دوستان خود، 10% سود از هر خرید آن‌ها دریافت کنید!\n\n🔗 لینک اختصاصی شما:\n`https://t.me/{bot_username}?start={chat_id}`\n\n💰 سود شما مستقیماً به کیف پول ربات واریز می‌شود.",
        'wallet_title': "💰 **شارژ کیف پول**\n\nجهت شارژ حساب، مبلغ مورد نظر را به یکی از آدرس‌های زیر واریز کرده و رسید یا TXID را برای پشتیبانی ارسال کنید:\n\n🔹 **Tether (USDT-TRC20):**\n`T-ADDRESS-HERE`\n\n🔹 **TON:**\n`TON-ADDRESS-HERE`",
        'buy_title': "🛒 **انتخاب پلن اشتراک**\n\nلطفاً یکی از پلن‌های پرسرعت زیر را انتخاب کنید:",
        'support_msg': "🎧 جهت ارتباط با واحد پشتیبانی و ارسال رسید پرداخت، با آیدی زیر در تماس باشید:\n\n🆔 @Nova_Support_Admin",
        'lang_set': "زبان به فارسی تغییر کرد. 🇮🇷"
    },
    'en': {
        'welcome': "💎 Welcome to Nova VPN!",
        'choose_lang': "Please select your language:",
        'main_menu': "🏠 Main Menu\n➖➖➖➖➖➖\n💰 Balance: {balance} Tomans\n👥 Referrals: {ref_count}",
        'btn_buy': "🛒 Buy VIP Plan",
        'btn_dash': "👤 My Dashboard",
        'btn_wallet': "💰 Wallet / Top-up",
        'btn_affiliate': "🤝 Affiliate Program",
        'btn_support': "🎧 Support",
        'btn_lang': "🌐 تغییر زبان",
        'dash_title': "👤 **Your Dashboard**\n\n🆔 ID: `{chat_id}`\n💰 Balance: {balance} Tomans\n📅 Joined: {date}\n\n📦 **Your Active Services:**\n{services}",
        'no_services': "❌ You have no active subscriptions.",
        'affiliate_title': "🤝 **Nova Affiliate Program**\n\nInvite your friends and earn 10% commission on every purchase!\n\n🔗 Your Referral Link:\n`https://t.me/{bot_username}?start={chat_id}`\n\n💰 Rewards are added to your bot wallet.",
        'wallet_title': "💰 **Wallet Top-up**\n\nTo charge your account, send the amount to one of the addresses below and share the receipt/TXID with support:\n\n🔹 **Tether (USDT-TRC20):**\n`T-ADDRESS-HERE`\n\n🔹 **TON:**\n`TON-ADDRESS-HERE`",
        'buy_title': "🛒 **Select a Plan**\n\nPlease choose from our high-speed plans below:",
        'support_msg': "🎧 To contact support or send payment receipts, use the ID below:\n\n🆔 @Nova_Support_Admin",
        'lang_set': "Language set to English. 🇬🇧"
    }
}

# ==========================================
# 🛠 توابع کمکی دیتابیس
# ==========================================

def get_user(chat_id):
    res = requests.get(f"{URL}/rest/v1/users?chat_id=eq.{chat_id}&select=*", headers=DB_HEADERS)
    return res.json()[0] if res.json() else None

def get_active_plans(chat_id):
    res = requests.get(f"{URL}/rest/v1/configs?owner_id=eq.{chat_id}&status=eq.sold&select=*", headers=DB_HEADERS)
    return res.json()

def get_available_plans():
    res = requests.get(f"{URL}/rest/v1/plans?is_active=eq.true&select=*", headers=DB_HEADERS)
    return res.json()

def build_main_menu(user):
    lang = user.get('language', 'fa')
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    s = STRINGS[lang]
    markup.row(s['btn_buy'])
    markup.row(s['btn_dash'], s['btn_wallet'])
    markup.row(s['btn_affiliate'], s['btn_support'])
    markup.row(s['btn_lang'])
    if user.get('role') == 'admin': markup.row("🛠 Admin Panel")
    return markup

# ==========================================
# 🤖 هندلرهای دستورات
# ==========================================

@bot.message_handler(commands=['start'])
def start_cmd(message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    
    # بررسی Referral (دعوت)
    ref_id = None
    if len(message.text.split()) > 1:
        potential_ref = message.text.split()[1]
        if potential_ref.isdigit() and int(potential_ref) != chat_id:
            ref_id = int(potential_ref)

    if not user:
        role = 'admin' if str(chat_id) == ADMIN_ID else 'user'
        new_user = {
            'chat_id': chat_id,
            'username': message.from_user.username,
            'role': role,
            'language': 'fa',
            'referrer_id': ref_id
        }
        requests.post(f"{URL}/rest/v1/users", headers=DB_HEADERS, json=new_user)
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa"),
                   telebot.types.InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"))
        bot.send_message(chat_id, STRINGS['fa']['welcome'] + "\n\n" + STRINGS['fa']['choose_lang'], reply_markup=markup)
    else:
        lang = user.get('language', 'fa')
        text = STRINGS[lang]['main_menu'].format(balance=user.get('wallet_balance', 0), ref_count=user.get('total_referrals', 0))
        bot.send_message(chat_id, text, reply_markup=build_main_menu(user), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('setlang_'))
def callback_lang(call):
    chat_id = call.message.chat.id
    new_lang = call.data.split('_')[1]
    requests.patch(f"{URL}/rest/v1/users?chat_id=eq.{chat_id}", headers=DB_HEADERS, json={'language': new_lang})
    bot.delete_message(chat_id, call.message.message_id)
    user = get_user(chat_id)
    bot.send_message(chat_id, STRINGS[new_lang]['lang_set'], reply_markup=build_main_menu(user))

# ==========================================
# 🔘 هندلرهای دکمه‌های منو
# ==========================================

@bot.message_handler(func=lambda m: True)
def menu_controller(message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    if not user: return
    
    lang = user.get('language', 'fa')
    text = message.text
    s = STRINGS[lang]

    # --- دکمه داشبورد ---
    if text == s['btn_dash']:
        plans = get_active_plans(chat_id)
        services_text = ""
        if plans:
            for p in plans:
                services_text += f"🔹 {p['plan_name']} | [Panel Link]({p['web_panel_url']})\n"
        else:
            services_text = s['no_services']
        
        dash_msg = s['dash_title'].format(
            chat_id=chat_id, 
            balance=user.get('wallet_balance', 0), 
            date=user.get('joined_at', 'N/A')[:10],
            services=services_text
        )
        bot.send_message(chat_id, dash_msg, parse_mode="Markdown", disable_web_page_preview=True)

    # --- دکمه خرید ---
    elif text == s['btn_buy']:
        plans_data = get_available_plans()
        markup = telebot.types.InlineKeyboardMarkup()
        for p in plans_data:
            title = p['title_fa'] if lang == 'fa' else p['title_en']
            markup.row(telebot.types.InlineKeyboardButton(f"{title} - {p['price_toman']} T", callback_data=f"buy_{p['internal_name']}"))
        bot.send_message(chat_id, s['buy_title'], reply_markup=markup, parse_mode="Markdown")

    # --- دکمه کیف پول ---
    elif text == s['btn_wallet']:
        bot.send_message(chat_id, s['wallet_title'], parse_mode="Markdown")

    # --- دکمه زیرمجموعه‌گیری ---
    elif text == s['btn_affiliate']:
        bot_info = bot.get_me()
        aff_msg = s['affiliate_title'].format(bot_username=bot_info.username, chat_id=chat_id)
        bot.send_message(chat_id, aff_msg, parse_mode="Markdown")

    # --- دکمه پشتیبانی ---
    elif text == s['btn_support']:
        bot.send_message(chat_id, s['support_msg'])

    # --- تغییر زبان ---
    elif text in [STRINGS['fa']['btn_lang'], STRINGS['en']['btn_lang']]:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa"),
                   telebot.types.InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"))
        bot.send_message(chat_id, "Select Language / انتخاب زبان:", reply_markup=markup)

# ==========================================
# 🌐 مسیرهای وب‌سرور
# ==========================================

@app.route('/', methods=['GET'])
def index(): return "✅ Nova VPN Bot is fully operational!"

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
