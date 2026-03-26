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

# استفاده از Session برای افزایش سرعت درخواست‌ها به دیتابیس
db_session = requests.Session()
bot = telebot.TeleBot(TOKEN, threaded=False)

# هدرهای مورد نیاز برای ارتباط با Supabase REST API
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
        return f"{int(amount):,}"
    except:
        return str(amount)

def get_user(chat_id):
    """دریافت اطلاعات کاربر با استفاده از سشن برای سرعت بیشتر"""
    try:
        res = db_session.get(f"{URL}/rest/v1/users?chat_id=eq.{chat_id}&select=*", headers=DB_HEADERS, timeout=5)
        return res.json()[0] if res.json() else None
    except:
        return None

def get_available_plans():
    try:
        res = db_session.get(f"{URL}/rest/v1/plans?is_active=eq.true&select=*", headers=DB_HEADERS, timeout=5)
        return res.json()
    except:
        return []

def build_main_menu(user):
    lang = user.get('language', 'fa')
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    s = STRINGS[lang]
    markup.row(s['btn_buy'])
    markup.row(s['btn_dash'], s['btn_wallet'])
    markup.row(s['btn_affiliate'], s['btn_support'])
    markup.row(s['btn_lang'])
    if str(user['chat_id']) == ADMIN_ID: markup.row("🛠 Admin Panel")
    return markup

# ==========================================
# 📝 دیکشنری متون
# ==========================================
STRINGS = {
    'fa': {
        'intro': (
            "🚀 **به نُوا وی‌پی‌ان خوش آمدید | Nova VPN**\n\n"
            "ما مفتخریم که سریع‌ترین و امن‌ترین زیرساخت اینترنت آزاد را در اختیار شما قرار می‌دهیم.\n\n"
            "📢 **کانال رسمی:** @NovaVPN_Net\n"
            "🎧 **پشتیبانی:** @NovaVPN_Sup\n\n"
            "👇 **لطفاً برای ادامه کار، زبان خود را انتخاب کنید:**"
        ),
        'welcome': "💎 خوش آمدید! هم‌اکنون می‌توانید از منوی زیر استفاده کنید.",
        'main_menu': "🏠 **منوی اصلی مدیریت**\n➖➖➖➖➖➖\n💰 موجودی: `{balance}` تومان\n👥 زیرمجموعه: `{ref_count}` نفر",
        'btn_buy': "🛒 خرید اشتراک VIP",
        'btn_dash': "👤 داشبورد من",
        'btn_wallet': "💰 کیف پول / شارژ",
        'btn_affiliate': "🤝 کسب درآمد",
        'btn_support': "🎧 پشتیبانی",
        'btn_lang': "🌐 Change Language",
        'dash_title': "👤 **داشبورد نُوا**\n\n🆔 آیدی: `{chat_id}`\n💰 اعتبار: `{balance}` تومان\n\n📦 **سرویس‌های شما:**\n{services}",
        'wallet_title': (
            "💰 **شارژ حساب (کمترین کارمزد)**\n\n"
            "لطفاً مبلغ مورد نظر را به یکی از آدرس‌های زیر واریز کنید:\n\n"
            "🔹 **TRON (TRX):**\n`TSgfCoCsrEXJs6RKkaCJF64wXpYVTRejZ3`\n\n"
            "🔹 **TON (Toncoin):**\n`UQCpWdG73bwuwFAp2EDQLLkl6VhTGpVVJDre8X02qvJ5OJem`\n\n"
            "🔹 **Tether (USDT-TRC20):**\n`TSgfCoCsrEXJs6RKkaCJF64wXpYVTRejZ3`\n\n"
            "🔹 **Ripple (XRP):**\n`rJ8A6gUZzwXm9XJv2fLaTGd6GkpBMdmm8F`\n\n"
            "⚠️ پس از واریز، فقط **هش تراکنش (TXID)** را در همینجا ارسال کنید."
        ),
        'invoice_msg': "🧾 **فاکتور خرید**\n📌 پلن: {plan}\n💵 مبلغ: {price} تومان\n\nلطفاً پرداخت را انجام داده و TXID را اینجا ارسال کنید:",
        'tx_received': "✅ تراکنش شما ثبت شد. پس از تایید توسط تیم مدیریت، سرویس به صورت خودکار برای شما ارسال و پورسانت معرف واریز می‌گردد.",
        'admin_panel': "🛠 **پنل مدیریت نُوا**",
        'sales_closed': "❌ متأسفانه در حال حاضر فروش موقتاً غیرفعال است.",
        'support_msg': "🎧 جهت ارتباط با واحد پشتیبانی و ارسال رسید، با آیدی زیر در تماس باشید:\n\n🆔 @NovaVPN_Sup"
    },
    'en': {
        'intro': "🚀 **Welcome to Nova VPN**\n\nPlease select your language to start:",
        'welcome': "💎 Welcome! You can now use the menu below.",
        'main_menu': "🏠 **Main Menu**\n➖➖➖➖➖➖\n💰 Balance: `{balance}` T\n👥 Referrals: `{ref_count}`",
        'btn_buy': "🛒 Buy VIP Plan",
        'btn_dash': "👤 My Dashboard",
        'btn_wallet': "💰 Wallet / Top-up",
        'btn_affiliate': "🤝 Affiliate",
        'btn_support': "🎧 Support",
        'btn_lang': "🌐 تغییر زبان",
        'dash_title': "👤 **Nova Dashboard**\n\n🆔 ID: `{chat_id}`\n💰 Balance: `{balance}` T\n\n📦 **Your Services:**\n{services}",
        'wallet_title': (
            "💰 **Wallet Top-up (Low Fees)**\n\n"
            "🔹 **TRX/USDT:** `TSgfCoCsrEXJs6RKkaCJF64wXpYVTRejZ3`\n"
            "🔹 **TON:** `UQCpWdG73bwuwFAp2EDQLLkl6VhTGpVVJDre8X02qvJ5OJem`\n"
            "🔹 **XRP:** `rJ8A6gUZzwXm9XJv2fLaTGd6GkpBMdmm8F`\n\n"
            "⚠️ Send **TXID** after payment."
        ),
        'invoice_msg': "🧾 **Invoice**\n📌 Plan: {plan}\n💵 Price: {price} T\n\nPlease pay and send TXID:",
        'tx_received': "✅ TX received. Pending admin approval.",
        'admin_panel': "🛠 **Nova Admin Panel**",
        'sales_closed': "❌ Sales are temporarily disabled.",
        'support_msg': "🎧 Support: @NovaVPN_Sup"
    }
}

# ==========================================
# 🤖 هندلرهای بهینه‌سازی شده
# ==========================================

@bot.message_handler(commands=['start'])
def start_cmd(message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    
    if not user:
        ref_id = None
        if len(message.text.split()) > 1:
            potential_ref = message.text.split()[1]
            if potential_ref.isdigit() and int(potential_ref) != chat_id:
                ref_id = int(potential_ref)

        role = 'admin' if str(chat_id) == ADMIN_ID else 'user'
        new_user = {
            'chat_id': chat_id, 'username': message.from_user.username,
            'role': role, 'language': 'fa', 'referrer_id': ref_id
        }
        db_session.post(f"{URL}/rest/v1/users", headers=DB_HEADERS, json=new_user)
        
        if ref_id:
            ref_user = get_user(ref_id)
            if ref_user:
                db_session.patch(f"{URL}/rest/v1/users?chat_id=eq.{ref_id}", headers=DB_HEADERS, 
                               json={'total_referrals': ref_user.get('total_referrals', 0) + 1})

        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa"),
                   telebot.types.InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"))
        bot.send_message(chat_id, STRINGS['fa']['intro'], reply_markup=markup, parse_mode="Markdown")
    else:
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
        bot.send_message(chat_id, STRINGS[new_lang]['welcome'], reply_markup=build_main_menu(user))

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
        bot.send_message(chat_id, STRINGS[user['language']]['tx_received'])
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton("✅ تایید و ارسال", callback_data=f"approve_{txid}"),
                   telebot.types.InlineKeyboardButton("❌ رد تراکنش", callback_data=f"reject_{txid}"))
        bot.send_message(ADMIN_ID, f"💰 **تراکنش جدید!**\nآیدی: `{chat_id}`\nهش: `{txid}`", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_', 'reject_')))
def admin_action(call):
    action, txid = call.data.split('_')
    if action == 'approve':
        tx_list = db_session.get(f"{URL}/rest/v1/transactions?txid_or_receipt=eq.{txid}", headers=DB_HEADERS).json()
        if not tx_list: return
        tx = tx_list[0]
        
        config = db_session.get(f"{URL}/rest/v1/configs?plan_name=eq.{tx['target_plan']}&status=eq.available&limit=1", headers=DB_HEADERS).json()
        
        if config:
            conf = config[0]
            db_session.patch(f"{URL}/rest/v1/configs?id=eq.{conf['id']}", headers=DB_HEADERS, json={'status': 'sold', 'owner_id': tx['chat_id']})
            db_session.patch(f"{URL}/rest/v1/transactions?id=eq.{tx['id']}", headers=DB_HEADERS, json={'status': 'approved'})
            
            buyer = get_user(tx['chat_id'])
            if buyer and buyer['referrer_id']:
                commission = int(tx['amount_toman'] * 0.1)
                ref_user = get_user(buyer['referrer_id'])
                if ref_user:
                    new_bal = ref_user['wallet_balance'] + commission
                    db_session.patch(f"{URL}/rest/v1/users?chat_id=eq.{buyer['referrer_id']}", headers=DB_HEADERS, json={'wallet_balance': new_bal})
                    bot.send_message(buyer['referrer_id'], f"🎊 **هدیه نُوا!**\nمبلغ `{f_price(commission)}` تومان پورسانت واریز شد.")

            bot.send_message(tx['chat_id'], f"🎉 **سرویس فعال شد!**\n\n🚀 کانفیگ:\n`{conf['v2ray_uri']}`\n\n📊 [پنل مدیریت حجم]({conf['web_panel_url']})", parse_mode="Markdown")
            bot.edit_message_text(f"✅ تایید شد: {txid}", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ انبار خالی است!", show_alert=True)
    else:
        bot.edit_message_text(f"❌ تراکنش رد شد: {txid}", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == "🛠 Admin Panel")
def admin_menu(message):
    if str(message.chat.id) != ADMIN_ID: return
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(telebot.types.InlineKeyboardButton("📦 مدیریت فروش پلن‌ها", callback_data="admin_manage_plans"))
    bot.send_message(message.chat.id, STRINGS['fa']['admin_panel'], reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_callbacks(call):
    if call.data == "admin_manage_plans":
        plans = db_session.get(f"{URL}/rest/v1/plans?select=*", headers=DB_HEADERS).json()
        markup = telebot.types.InlineKeyboardMarkup()
        for p in plans:
            status = "✅" if p['is_active'] else "❌"
            markup.row(telebot.types.InlineKeyboardButton(f"{status} | {p['title_fa']} ({f_price(p['price_toman'])})", callback_data=f"toggle_plan_{p['internal_name']}"))
        bot.edit_message_text("مدیریت وضعیت فروش:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif call.data.startswith("toggle_plan_"):
        p_name = call.data.replace("toggle_plan_", "")
        current = db_session.get(f"{URL}/rest/v1/plans?internal_name=eq.{p_name}", headers=DB_HEADERS).json()[0]
        db_session.patch(f"{URL}/rest/v1/plans?internal_name=eq.{p_name}", headers=DB_HEADERS, json={'is_active': not current['is_active']})
        admin_callbacks(telebot.types.CallbackQuery(id=call.id, from_user=call.from_user, message=call.message, data="admin_manage_plans", chat_instance=call.chat_instance, json=None))

@bot.message_handler(func=lambda m: True)
def menu_logic(message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    if not user: return
    lang = user['language']; s = STRINGS[lang]
    
    if message.text == s['btn_buy']:
        plans = get_available_plans()
        if not plans: 
            bot.send_message(chat_id, s['sales_closed'])
            return
        markup = telebot.types.InlineKeyboardMarkup()
        for p in plans:
            markup.row(telebot.types.InlineKeyboardButton(f"{p['title_fa']} - {f_price(p['price_toman'])} T", callback_data=f"buy_{p['internal_name']}"))
        bot.send_message(chat_id, s['buy_title'], reply_markup=markup, parse_mode="Markdown")
        
    elif message.text == s['btn_dash']:
        services = db_session.get(f"{URL}/rest/v1/configs?owner_id=eq.{chat_id}&select=*", headers=DB_HEADERS).json()
        srv_text = "\n".join([f"🔹 {s['plan_name']} | [پنل]({s['web_panel_url']})" for s in services]) if services else "سرویسی ندارید."
        bot.send_message(chat_id, s['dash_title'].format(chat_id=chat_id, balance=f_price(user['wallet_balance']), services=srv_text), parse_mode="Markdown")
        
    elif message.text == s['btn_wallet']:
        bot.send_message(chat_id, s['wallet_title'], parse_mode="Markdown")
        
    elif message.text == s['btn_affiliate']:
        bot_un = bot.get_me().username
        bot.send_message(chat_id, s['affiliate_title'].format(bot_username=bot_un, chat_id=chat_id), parse_mode="Markdown")
        
    elif message.text == s['btn_support']:
        bot.send_message(chat_id, s['support_msg'])

@app.route('/', methods=['GET'])
def index(): return "✅ Nova VPN is online!"

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
