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
# 📝 دیکشنری متون (دوزبانه با طراحی زیبا)
# ==========================================
STRINGS = {
    'fa': {
        'welcome': (
            "✨ **به دنیای اینترنت بدون مرز نُوا خوش آمدید!** ✨\n\n"
            "🚀 **نُوا وی‌پی‌ان (Nova VPN)**\n"
            "سریع‌ترین و پایدارترین راهکار برای دسترسی به اینترنت آزاد، گیمینگ و ترید.\n\n"
            "💎 **برخی از ویژگی‌های سرویس‌های ما:**\n"
            "✅ بهره‌گیری از پروتکل‌های نسل جدید\n"
            "✅ آپ‌تایم ۹۹.۹٪ و پایداری تضمینی\n"
            "✅ پنل اختصاصی مشاهده حجم تحت وب\n"
            "✅ پشتیبانی آنی و متخصص\n\n"
            "🌐 لطفاً جهت شروع، زبان مورد نظر خود را انتخاب کنید:"
        ),
        'choose_lang': "انتخاب زبان / Select Language:",
        'main_menu': "🏠 **منوی اصلی مدیریت اشتراک**\n➖➖➖➖➖➖\n💰 موجودی شما: `{balance}` تومان\n👥 تعداد زیرمجموعه: `{ref_count}` نفر",
        'btn_buy': "🛒 خرید اشتراک VIP",
        'btn_dash': "👤 داشبورد من",
        'btn_wallet': "💰 کیف پول / شارژ",
        'btn_affiliate': "🤝 کسب درآمد",
        'btn_support': "🎧 پشتیبانی",
        'btn_lang': "🌐 Change Language",
        'dash_title': "👤 **پنل کاربری شما**\n\n🆔 آیدی شما: `{chat_id}`\n💰 اعتبار: `{balance}` تومان\n📅 تاریخ عضویت: `{date}`\n\n📦 **سرویس‌های فعال شما:**\n{services}",
        'no_services': "❌ شما هنوز اشتراک فعالی ندارید.",
        'affiliate_title': "🤝 **سیستم کسب درآمد نُوا**\n\nبا دعوت دوستان خود، 10% سود از هر خرید آن‌ها دریافت کنید!\n\n🔗 لینک اختصاصی شما:\n`https://t.me/{bot_username}?start={chat_id}`\n\n💰 سود شما مستقیماً به کیف پول ربات واریز می‌شود.",
        'wallet_title': "💰 **شارژ کیف پول**\n\nجهت خرید یا شارژ حساب، مبلغ را واریز کرده و هش تراکنش (TXID) را ارسال کنید:\n\n🔹 **Tether (USDT-TRC20):**\n`T-ADDRESS-HERE`\n\n🔹 **TON:**\n`TON-ADDRESS-HERE`",
        'buy_title': "🛒 **انتخاب پلن اشتراک**\n\nلطفاً یکی از پلن‌های پرسرعت زیر را انتخاب کنید:",
        'invoice_msg': "🧾 **فاکتور خرید**\n\n📌 پلن: {plan}\n💵 مبلغ: {price} تومان\n\nلطفاً مبلغ را به ولت‌های بخش «کیف پول» واریز کرده و **فقط هش تراکنش (TXID)** را اینجا ارسال کنید:",
        'tx_received': "✅ تراکنش شما ثبت شد و در صف بررسی قرار گرفت. پس از تایید ادمین، سرویس برای شما ارسال می‌شود.",
        'support_msg': "🎧 جهت ارتباط با واحد پشتیبانی، با آیدی زیر در تماس باشید:\n\n🆔 @Nova_Support_Admin",
        'lang_set': "زبان با موفقیت به فارسی تغییر کرد. 🇮🇷"
    },
    'en': {
        'welcome': (
            "✨ **Welcome to the Borderless World of Nova VPN!** ✨\n\n"
            "🚀 **Nova VPN**\n"
            "The fastest and most stable solution for open internet, gaming, and trading.\n\n"
            "💎 **Key Features:**\n"
            "✅ Next-gen protocols\n"
            "✅ 99.9% Guaranteed Uptime\n"
            "✅ Dedicated Web Usage Dashboard\n"
            "✅ Instant Expert Support\n\n"
            "🌐 Please select your language to continue:"
        ),
        'choose_lang': "Select Language / انتخاب زبان:",
        'main_menu': "🏠 **Main Management Menu**\n➖➖➖➖➖➖\n💰 Balance: `{balance}` Tomans\n👥 Referrals: `{ref_count}`",
        'btn_buy': "🛒 Buy VIP Plan",
        'btn_dash': "👤 My Dashboard",
        'btn_wallet': "💰 Wallet / Top-up",
        'btn_affiliate': "🤝 Affiliate Program",
        'btn_support': "🎧 Support",
        'btn_lang': "🌐 تغییر زبان",
        'dash_title': "👤 **Your Dashboard**\n\n🆔 ID: `{chat_id}`\n💰 Balance: `{balance}` Tomans\n📅 Joined: `{date}`\n\n📦 **Your Active Services:**\n{services}",
        'no_services': "❌ You have no active subscriptions.",
        'affiliate_title': "🤝 **Nova Affiliate Program**\n\nInvite your friends and earn 10% commission!\n\n🔗 Your Link:\n`https://t.me/{bot_username}?start={chat_id}`",
        'wallet_title': "💰 **Wallet Top-up**\n\nSend the amount and share the TXID:\n\n🔹 **Tether (USDT-TRC20):**\n`T-ADDRESS-HERE`\n\n🔹 **TON:**\n`TON-ADDRESS-HERE`",
        'buy_title': "🛒 **Select a Plan**\n\nPlease choose a plan:",
        'invoice_msg': "🧾 **Invoice**\n\n📌 Plan: {plan}\n💵 Price: {price} Tomans\n\nPlease pay and send the **TXID** here:",
        'tx_received': "✅ Your transaction has been submitted for review. Service will be sent after approval.",
        'support_msg': "🎧 Contact support:\n\n🆔 @Nova_Support_Admin",
        'lang_set': "Language set to English. 🇬🇧"
    }
}

# ==========================================
# 🛠 توابع کمکی دیتابیس
# ==========================================

def get_user(chat_id):
    res = requests.get(f"{URL}/rest/v1/users?chat_id=eq.{chat_id}&select=*", headers=DB_HEADERS)
    return res.json()[0] if res.json() else None

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
    
    # بررسی Referral
    ref_id = None
    if len(message.text.split()) > 1:
        potential_ref = message.text.split()[1]
        if potential_ref.isdigit() and int(potential_ref) != chat_id:
            ref_id = int(potential_ref)

    if not user:
        role = 'admin' if str(chat_id) == ADMIN_ID else 'user'
        new_user = {
            'chat_id': chat_id, 'username': message.from_user.username,
            'role': role, 'language': 'fa', 'referrer_id': ref_id
        }
        requests.post(f"{URL}/rest/v1/users", headers=DB_HEADERS, json=new_user)
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa"),
                   telebot.types.InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"))
        
        # ارسال پیام خوش‌آمدگویی زیبا با فرمت Markdown
        bot.send_message(chat_id, STRINGS['fa']['welcome'], reply_markup=markup, parse_mode="Markdown")
    else:
        lang = user.get('language', 'fa')
        text = STRINGS[lang]['main_menu'].format(
            balance=user.get('wallet_balance', 0), 
            ref_count=user.get('total_referrals', 0)
        )
        bot.send_message(chat_id, text, reply_markup=build_main_menu(user), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('setlang_'))
def callback_lang(call):
    chat_id = call.message.chat.id
    new_lang = call.data.split('_')[1]
    requests.patch(f"{URL}/rest/v1/users?chat_id=eq.{chat_id}", headers=DB_HEADERS, json={'language': new_lang})
    bot.delete_message(chat_id, call.message.message_id)
    user = get_user(chat_id)
    bot.send_message(chat_id, STRINGS[new_lang]['lang_set'], reply_markup=build_main_menu(user), parse_mode="Markdown")

# ==========================================
# 🛒 سیستم خرید و تایید ادمین
# ==========================================

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_buy_plan(call):
    chat_id = call.message.chat.id
    plan_name = call.data.split('_', 1)[1]
    user = get_user(chat_id)
    lang = user['language']
    
    res = requests.get(f"{URL}/rest/v1/plans?internal_name=eq.{plan_name}", headers=DB_HEADERS).json()
    if not res: return
    plan = res[0]
    
    title = plan['title_fa'] if lang == 'fa' else plan['title_en']
    text = STRINGS[lang]['invoice_msg'].format(plan=title, price=plan['price_toman'])
    
    new_tx = {
        'chat_id': chat_id,
        'amount_toman': plan['price_toman'],
        'target_plan': plan_name,
        'status': 'pending',
        'txid_or_receipt': 'AWAITING_TXID'
    }
    requests.post(f"{URL}/rest/v1/transactions", headers=DB_HEADERS, json=new_tx)
    
    bot.edit_message_text(text, chat_id, call.message.message_id, parse_mode="Markdown")

@bot.message_handler(func=lambda m: len(m.text) > 20)
def handle_txid_submission(message):
    chat_id = message.chat.id
    txid = message.text.strip()
    user = get_user(chat_id)
    if not user: return
    lang = user['language']
    
    update_url = f"{URL}/rest/v1/transactions?chat_id=eq.{chat_id}&txid_or_receipt=eq.AWAITING_TXID"
    res = requests.patch(update_url, headers=DB_HEADERS, json={'txid_or_receipt': txid})
    
    if res.status_code in [200, 201, 204]:
        bot.send_message(chat_id, STRINGS[lang]['tx_received'], parse_mode="Markdown")
        
        admin_markup = telebot.types.InlineKeyboardMarkup()
        admin_markup.row(
            telebot.types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_{txid}"),
            telebot.types.InlineKeyboardButton("❌ رد", callback_data=f"reject_{txid}")
        )
        admin_text = f"🚨 **تراکنش جدید!**\n\n👤 کاربر: `{chat_id}`\n🔗 TXID: `{txid}`\n\nلطفا تراکنش را بررسی و تایید کنید."
        bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_', 'reject_')))
def admin_action(call):
    action, txid = call.data.split('_')
    
    if action == 'approve':
        tx_res = requests.get(f"{URL}/rest/v1/transactions?txid_or_receipt=eq.{txid}", headers=DB_HEADERS).json()
        if not tx_res: return
        tx = tx_res[0]
        
        config_res = requests.get(f"{URL}/rest/v1/configs?plan_name=eq.{tx['target_plan']}&status=eq.available&limit=1", headers=DB_HEADERS).json()
        
        if config_res:
            config = config_res[0]
            requests.patch(f"{URL}/rest/v1/configs?id=eq.{config['id']}", headers=DB_HEADERS, 
                           json={'status': 'sold', 'owner_id': tx['chat_id']})
            requests.patch(f"{URL}/rest/v1/transactions?id=eq.{tx['id']}", headers=DB_HEADERS, json={'status': 'approved'})
            
            bot.send_message(tx['chat_id'], f"🎉 **پرداخت شما تایید شد!**\n\n🚀 کانفیگ اختصاصی شما:\n`{config['v2ray_uri']}`\n\n📊 [لینک پنل مشاهده حجم]({config['web_panel_url']})", parse_mode="Markdown")
            bot.edit_message_text(f"✅ تراکنش `{txid}` تایید و سرویس ارسال شد.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "❌ خطا: موجودی این پلن در انبار تمام شده است!")
    else:
        bot.edit_message_text(f"❌ تراکنش `{txid}` توسط شما رد شد.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# ==========================================
# 🔘 سایر دکمه‌های منو
# ==========================================

@bot.message_handler(func=lambda m: True)
def menu_controller(message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    if not user: return
    lang = user['language']; s = STRINGS[lang]
    
    if message.text == s['btn_dash']:
        bot.send_message(chat_id, s['dash_title'].format(chat_id=chat_id, balance=user['wallet_balance'], date=user['joined_at'][:10], services="جهت مشاهده وضعیت مصرف روی لینک‌های بالا کلیک کنید."), parse_mode="Markdown")
    elif message.text == s['btn_buy']:
        plans = get_available_plans()
        markup = telebot.types.InlineKeyboardMarkup()
        for p in plans:
            markup.row(telebot.types.InlineKeyboardButton(f"{p['title_fa']} - {p['price_toman']} T", callback_data=f"buy_{p['internal_name']}"))
        bot.send_message(chat_id, s['buy_title'], reply_markup=markup, parse_mode="Markdown")
    elif message.text == s['btn_wallet']:
        bot.send_message(chat_id, s['wallet_title'], parse_mode="Markdown")
    elif message.text == s['btn_affiliate']:
        bot_info = bot.get_me()
        bot.send_message(chat_id, s['affiliate_title'].format(bot_username=bot_info.username, chat_id=chat_id), parse_mode="Markdown")
    elif message.text == s['btn_support']:
        bot.send_message(chat_id, s['support_msg'])
    elif message.text in [STRINGS['fa']['btn_lang'], STRINGS['en']['btn_lang']]:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa"),
                   telebot.types.InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"))
        bot.send_message(chat_id, s['choose_lang'], reply_markup=markup)

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
