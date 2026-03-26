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
BOT_USERNAME = "NoovaVpn_Bot" # جایگزین آیدی ربات شما برای سرعت بیشتر

# استفاده از Session برای افزایش سرعت و پایداری اتصالات
db_session = requests.Session()
bot = telebot.TeleBot(TOKEN, threaded=False)

# هدرهای ثابت برای ارتباط با دیتابیس
DB_HEADERS = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ==========================================
# 🛠 توابع کمکی بهینه‌سازی شده
# ==========================================

def f_price(amount):
    """فرمت‌دهی اعداد به صورت ۳ رقم ۳ رقم"""
    try:
        return f"{int(amount or 0):,}"
    except:
        return str(amount or 0)

def get_user(chat_id):
    """دریافت سریع اطلاعات کاربر از دیتابیس"""
    try:
        res = db_session.get(f"{URL}/rest/v1/users?chat_id=eq.{chat_id}&select=*", headers=DB_HEADERS, timeout=5)
        data = res.json()
        return data[0] if data else None
    except Exception as e:
        print(f"DB Error (get_user): {e}")
        return None

def get_available_plans():
    """دریافت لیست پلن‌های فعال"""
    try:
        res = db_session.get(f"{URL}/rest/v1/plans?is_active=eq.true&select=*", headers=DB_HEADERS, timeout=5)
        return res.json()
    except:
        return []

def build_main_menu(user):
    """ساخت منوی اصلی بر اساس نقش و زبان کاربر"""
    lang = user.get('language', 'fa')
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    s = STRINGS[lang]
    
    markup.row(s['btn_buy'])
    markup.row(s['btn_dash'], s['btn_wallet'])
    markup.row(s['btn_affiliate'], s['btn_support'])
    markup.row(s['btn_lang'])
    
    # نمایش دکمه مدیریت فقط برای ادمین اصلی
    if str(user.get('chat_id')) == ADMIN_ID:
        markup.row("🛠 Admin Panel")
    return markup

# ==========================================
# 📝 دیکشنری متون (دوزبانه و حرفه‌ای)
# ==========================================
STRINGS = {
    'fa': {
        'intro': (
            "🚀 **خوش آمدید به نُوا وی‌پی‌ان | Nova VPN**\n"
            "➖➖➖➖➖➖➖➖➖➖\n"
            "💎 **چرا نُوا را انتخاب کنیم؟**\n"
            "✅ سرعت فوق‌العاده با پروتکل‌های V2Ray\n"
            "✅ مخصوص گیمینگ، ترید و اینستاگرام\n"
            "✅ بدون قطعی و افت سرعت (Dedicated)\n"
            "✅ پشتیبانی آنی و ۲۴ ساعته\n\n"
            "📢 **کانال اطلاع‌رسانی:** @NovaVPN_Net\n"
            "🎧 **واحد پشتیبانی:** @NovaVPN_Sup\n"
            "🤖 **آیدی ربات:** @NoovaVpn_Bot\n"
            "➖➖➖➖➖➖➖➖➖➖\n"
            "👇 **لطفاً جهت ادامه، زبان خود را انتخاب کنید:**"
        ),
        'welcome': "💎 **نُوا با موفقیت فعال شد!**\nهم‌اکنون می‌توانید از منوی هوشمند زیر استفاده کنید.",
        'main_menu': "🏠 **پنل مدیریت اشتراک**\n➖➖➖➖➖➖\n💰 موجودی: `{balance}` تومان\n👥 زیرمجموعه: `{ref_count}` نفر",
        'btn_buy': "🛒 خرید اشتراک VIP",
        'btn_dash': "👤 داشبورد من",
        'btn_wallet': "💰 کیف پول / شارژ",
        'btn_affiliate': "🤝 کسب درآمد",
        'btn_support': "🎧 پشتیبانی",
        'btn_lang': "🌐 Change Language",
        'dash_title': "👤 **داشبورد نُوا**\n\n🆔 آیدی: `{chat_id}`\n💰 اعتبار: `{balance}` تومان\n\n📦 **سرویس‌های شما:**\n{services}",
        'wallet_title': (
            "💰 **شارژ حساب (کمترین کارمزد)**\n\n"
            "لطفاً مبلغ را به یکی از ولت‌های زیر واریز کنید:\n\n"
            "🔹 **TRON (TRX):**\n`TSgfCoCsrEXJs6RKkaCJF64wXpYVTRejZ3`\n\n"
            "🔹 **TON (Toncoin):**\n`UQCpWdG73bwuwFAp2EDQLLkl6VhTGpVVJDre8X02qvJ5OJem`\n\n"
            "🔹 **Tether (USDT-TRC20):**\n`TSgfCoCsrEXJs6RKkaCJF64wXpYVTRejZ3`\n\n"
            "🔹 **Ripple (XRP):**\n`rJ8A6gUZzwXm9XJv2fLaTGd6GkpBMdmm8F`\n\n"
            "⚠️ پس از واریز، فقط **هش تراکنش (TXID)** را در اینجا ارسال کنید."
        ),
        'invoice_msg': "🧾 **فاکتور خرید**\n📌 پلن: {plan}\n💵 مبلغ: {price} تومان\n\nلطفاً مبلغ را واریز و TXID را اینجا بفرستید:",
        'tx_received': "✅ تراکنش با موفقیت ثبت شد و در صف تایید قرار گرفت. پورسانت معرف نیز پس از تایید واریز می‌گردد.",
        'admin_panel': "🛠 **پنل مدیریت نُوا**\nیکی از بخش‌ها را جهت نظارت انتخاب کنید:",
        'sales_closed': "❌ در حال حاضر فروش موقتاً غیرفعال است.",
        'support_msg': "🎧 جهت ارتباط با واحد پشتیبانی و ارسال رسید، با آیدی زیر در تماس باشید:\n\n🆔 @NovaVPN_Sup",
        'lang_set': "زبان با موفقیت به فارسی تغییر کرد. 🇮🇷"
    },
    'en': {
        'intro': "🚀 **Welcome to Nova VPN**\n\nPlease select your language to start:",
        'welcome': "💎 **Nova is ready!**\nUse the menu below to manage your account.",
        'main_menu': "🏠 **Account Dashboard**\n➖➖➖➖➖➖\n💰 Balance: `{balance}` T\n👥 Referrals: `{ref_count}`",
        'btn_buy': "🛒 Buy VIP Plan",
        'btn_dash': "👤 My Dashboard",
        'btn_wallet': "💰 Wallet / Top-up",
        'btn_affiliate': "🤝 Affiliate",
        'btn_support': "🎧 Support",
        'btn_lang': "🌐 تغییر زبان",
        'dash_title': "👤 **Nova Dashboard**\n\n🆔 ID: `{chat_id}`\n💰 Balance: `{balance}` T\n\n📦 **Your Services:**\n{services}",
        'wallet_title': "💰 **Wallet Top-up**\nPlease send payment and share TXID here.",
        'invoice_msg': "🧾 **Invoice**\n📌 Plan: {plan}\n💵 Price: {price} T\n\nSend TXID after payment:",
        'tx_received': "✅ TX received. Processing for admin approval...",
        'admin_panel': "🛠 **Nova Admin Panel**",
        'sales_closed': "❌ Sales are currently disabled.",
        'support_msg': "🎧 Support: @NovaVPN_Sup",
        'lang_set': "Language set to English. 🇬🇧"
    }
}

# ==========================================
# 🤖 هندلرهای تلگرام (بهینه‌سازی شده برای وب‌هوک)
# ==========================================

@bot.message_handler(commands=['start'])
def start_cmd(message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    
    # مدیریت سیستم رفرال
    ref_id = None
    if len(message.text.split()) > 1:
        potential_ref = message.text.split()[1]
        if potential_ref.isdigit() and int(potential_ref) != chat_id:
            ref_id = int(potential_ref)

    if not user:
        # ثبت کاربر جدید
        role = 'admin' if str(chat_id) == ADMIN_ID else 'user'
        new_user = {
            'chat_id': chat_id, 'username': message.from_user.username,
            'role': role, 'language': 'fa', 'referrer_id': ref_id
        }
        db_session.post(f"{URL}/rest/v1/users", headers=DB_HEADERS, json=new_user)
        
        # افزایش تعداد زیرمجموعه معرف
        if ref_id:
            ru = get_user(ref_id)
            if ru:
                db_session.patch(f"{URL}/rest/v1/users?chat_id=eq.{ref_id}", headers=DB_HEADERS, 
                               json={'total_referrals': ru.get('total_referrals', 0) + 1})

        # نمایش پیام معرفی و انتخاب زبان
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa"),
                   telebot.types.InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"))
        bot.send_message(chat_id, STRINGS['fa']['intro'], reply_markup=markup, parse_mode="Markdown")
    else:
        # اگر کاربر وجود داشت، منوی اصلی را نشان می‌دهیم
        lang = user.get('language', 'fa')
        text = STRINGS[lang]['main_menu'].format(balance=f_price(user.get('wallet_balance', 0)), ref_count=user.get('total_referrals', 0))
        bot.send_message(chat_id, text, reply_markup=build_main_menu(user), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('setlang_'))
def callback_lang(call):
    chat_id = call.message.chat.id
    new_lang = call.data.split('_')[1]
    db_session.patch(f"{URL}/rest/v1/users?chat_id=eq.{chat_id}", headers=DB_HEADERS, json={'language': new_lang})
    bot.delete_message(chat_id, call.message.message_id)
    user = get_user(chat_id)
    if user:
        bot.send_message(chat_id, STRINGS[new_lang]['welcome'], reply_markup=build_main_menu(user), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_buy_plan(call):
    chat_id = call.message.chat.id
    plan_name = call.data.split('_', 1)[1]
    user = get_user(chat_id)
    if not user: return
    
    lang = user['language']
    res = db_session.get(f"{URL}/rest/v1/plans?internal_name=eq.{plan_name}", headers=DB_HEADERS).json()
    if not res: return
    plan = res[0]
    
    if not plan['is_active']:
        bot.answer_callback_query(call.id, STRINGS[lang]['sales_closed'], show_alert=True)
        return

    text = STRINGS[lang]['invoice_msg'].format(plan=plan['title_fa'], price=f_price(plan['price_toman']))
    db_session.post(f"{URL}/rest/v1/transactions", headers=DB_HEADERS, json={
        'chat_id': chat_id, 'amount_toman': plan['price_toman'],
        'target_plan': plan_name, 'status': 'pending', 'txid_or_receipt': 'AWAITING'
    })
    bot.edit_message_text(text, chat_id, call.message.message_id, parse_mode="Markdown")

@bot.message_handler(func=lambda m: len(m.text) > 20)
def handle_txid(message):
    chat_id = message.chat.id
    txid = message.text.strip()
    user = get_user(chat_id)
    if not user: return
    
    update_url = f"{URL}/rest/v1/transactions?chat_id=eq.{chat_id}&txid_or_receipt=eq.AWAITING"
    res = db_session.patch(update_url, headers=DB_HEADERS, json={'txid_or_receipt': txid})
    
    if res.status_code < 300:
        bot.send_message(chat_id, STRINGS[user['language']]['tx_received'], parse_mode="Markdown")
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton("✅ تایید و تحویل", callback_data=f"approve_{txid}"),
                   telebot.types.InlineKeyboardButton("❌ رد تراکنش", callback_data=f"reject_{txid}"))
        bot.send_message(ADMIN_ID, f"💰 **تراکنش جدید!**\nکاربر: `{chat_id}`\nهش: `{txid}`", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_', 'reject_')))
def admin_action(call):
    action, txid = call.data.split('_')
    if action == 'approve':
        tx_list = db_session.get(f"{URL}/rest/v1/transactions?txid_or_receipt=eq.{txid}", headers=DB_HEADERS).json()
        if not tx_list: return
        tx = tx_list[0]
        
        # پیدا کردن اولین کانفیگ موجود در انبار
        config = db_session.get(f"{URL}/rest/v1/configs?plan_name=eq.{tx['target_plan']}&status=eq.available&limit=1", headers=DB_HEADERS).json()
        
        if config:
            conf = config[0]
            db_session.patch(f"{URL}/rest/v1/configs?id=eq.{conf['id']}", headers=DB_HEADERS, json={'status': 'sold', 'owner_id': tx['chat_id']})
            db_session.patch(f"{URL}/rest/v1/transactions?id=eq.{tx['id']}", headers=DB_HEADERS, json={'status': 'approved'})
            
            # پرداخت پورسانت ۱۰ درصدی رفرال
            buyer = get_user(tx['chat_id'])
            if buyer and buyer['referrer_id']:
                commission = int(tx['amount_toman'] * 0.1)
                ru = get_user(buyer['referrer_id'])
                if ru:
                    new_bal = ru.get('wallet_balance', 0) + commission
                    db_session.patch(f"{URL}/rest/v1/users?chat_id=eq.{buyer['referrer_id']}", headers=DB_HEADERS, json={'wallet_balance': new_bal})
                    bot.send_message(buyer['referrer_id'], f"🎊 **پورسانت واریز شد!**\nمبلغ `{f_price(commission)}` تومان بابت خرید زیرمجموعه به کیف پول شما اضافه شد.")

            bot.send_message(tx['chat_id'], f"🎉 **سرویس شما فعال شد!**\n\n🚀 کانفیگ اختصاصی:\n`{conf['v2ray_uri']}`\n\n📊 [پنل مدیریت حجم]({conf['web_panel_url']})", parse_mode="Markdown")
            bot.edit_message_text(f"✅ تایید شد: `{txid}`", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "❌ انبار خالی است! ابتدا کانفیگ اضافه کنید.", show_alert=True)
    else:
        bot.edit_message_text(f"❌ تراکنش رد شد: `{txid}`", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# ==========================================
# 🛠 پنل مدیریت (Admin Panel)
# ==========================================

@bot.message_handler(func=lambda m: m.text == "🛠 Admin Panel")
def admin_menu(message):
    if str(message.chat.id) != ADMIN_ID: return
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(telebot.types.InlineKeyboardButton("📦 مدیریت فروش پلن‌ها", callback_data="admin_manage_plans"))
    bot.send_message(message.chat.id, STRINGS['fa']['admin_panel'], reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_callbacks(call):
    if str(call.message.chat.id) != ADMIN_ID: return
    if call.data == "admin_manage_plans":
        plans = db_session.get(f"{URL}/rest/v1/plans?select=*", headers=DB_HEADERS).json()
        markup = telebot.types.InlineKeyboardMarkup()
        for p in plans:
            status = "✅" if p['is_active'] else "❌"
            markup.row(telebot.types.InlineKeyboardButton(f"{status} | {p['title_fa']} ({f_price(p['price_toman'])})", callback_data=f"toggle_plan_{p['internal_name']}"))
        bot.edit_message_text("وضعیت فروش پلن‌ها را تغییر دهید:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif call.data.startswith("toggle_plan_"):
        p_name = call.data.replace("toggle_plan_", "")
        current = db_session.get(f"{URL}/rest/v1/plans?internal_name=eq.{p_name}", headers=DB_HEADERS).json()[0]
        db_session.patch(f"{URL}/rest/v1/plans?internal_name=eq.{p_name}", headers=DB_HEADERS, json={'is_active': not current['is_active']})
        admin_callbacks(telebot.types.CallbackQuery(id=call.id, from_user=call.from_user, message=call.message, data="admin_manage_plans", chat_instance=call.chat_instance, json=None))

# ==========================================
# 🔘 مدیریت منطق دکمه‌های منو
# ==========================================

@bot.message_handler(func=lambda m: True)
def menu_logic(message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    if not user: return
    
    lang = user.get('language', 'fa')
    text = message.text
    s = STRINGS[lang]
    
    # بررسی دکمه‌های منو
    if text == s['btn_buy']:
        plans = get_available_plans()
        if not plans: 
            bot.send_message(chat_id, s['sales_closed'])
            return
        markup = telebot.types.InlineKeyboardMarkup()
        for p in plans:
            markup.row(telebot.types.InlineKeyboardButton(f"{p['title_fa']} - {f_price(p['price_toman'])} T", callback_data=f"buy_{p['internal_name']}"))
        bot.send_message(chat_id, s['buy_title'], reply_markup=markup, parse_mode="Markdown")
        
    elif text == s['btn_dash']:
        services = db_session.get(f"{URL}/rest/v1/configs?owner_id=eq.{chat_id}&select=*", headers=DB_HEADERS).json()
        srv_text = "\n".join([f"🔹 {s['plan_name']} | [پنل]({s['web_panel_url']})" for s in services]) if services else s['no_services']
        bot.send_message(chat_id, s['dash_title'].format(chat_id=chat_id, balance=f_price(user['wallet_balance']), services=srv_text), parse_mode="Markdown", disable_web_page_preview=True)
        
    elif text == s['btn_wallet']:
        bot.send_message(chat_id, s['wallet_title'], parse_mode="Markdown")
        
    elif text == s['btn_affiliate']:
        aff_msg = s['affiliate_title'].format(bot_username=BOT_USERNAME, chat_id=chat_id)
        bot.send_message(chat_id, aff_msg, parse_mode="Markdown")
        
    elif text == s['btn_support']:
        bot.send_message(chat_id, s['support_msg'])
        
    elif text == s['btn_lang']:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa"),
                   telebot.types.InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"))
        bot.send_message(chat_id, "Select Language / انتخاب زبان:", reply_markup=markup)

# ==========================================
# 🌐 Flask Routes (Vercel Entry Points)
# ==========================================

@app.route('/', methods=['GET'])
def index(): return "✅ Nova VPN Backend is Online!"

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
