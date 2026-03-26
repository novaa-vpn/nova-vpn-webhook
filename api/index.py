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
# 📝 دیکشنری متون
# ==========================================
STRINGS = {
    'fa': {
        'intro': (
            "🚀 **به نُوا وی‌پی‌ان خوش آمدید | Nova VPN**\n\n"
            "ما مفتخریم که سریع‌ترین و امن‌ترین زیرساخت اینترنت آزاد را در اختیار شما قرار می‌دهیم.\n\n"
            "💎 **چرا نُوا؟**\n"
            "🔹 سرورهای اختصاصی با پورت ۱۰ گیگابیت\n"
            "🔹 بدون قطعی و افت سرعت در ساعات اوج مصرف\n"
            "🔹 پشتیبانی ۲۴ ساعته واقعی\n"
            "🔹 قابلیت استفاده در تمام سیستم‌عامل‌ها\n\n"
            "📢 **کانال ما:** @NovaVPN_Net\n"
            "🎧 **پشتیبانی:** @NovaVPN_Sup\n\n"
            "👇 **لطفاً برای ادامه کار، زبان خود را انتخاب کنید:**"
        ),
        'welcome': "💎 خوش آمدید! هم‌اکنون می‌توانید از منوی زیر استفاده کنید.",
        'main_menu': "🏠 **منوی اصلی**\n➖➖➖➖➖➖\n💰 موجودی: `{balance}` تومان\n👥 زیرمجموعه: `{ref_count}` نفر",
        'btn_buy': "🛒 خرید اشتراک VIP",
        'btn_dash': "👤 داشبورد من",
        'btn_wallet': "💰 کیف پول / شارژ",
        'btn_affiliate': "🤝 کسب درآمد",
        'btn_support': "🎧 پشتیبانی",
        'btn_lang': "🌐 Change Language",
        'dash_title': "👤 **داشبورد نُوا**\n\n🆔 آیدی: `{chat_id}`\n💰 اعتبار: `{balance}` تومان\n\n📦 **سرویس‌های شما:**\n{services}",
        'wallet_title': (
            "💰 **شارژ حساب (کمترین کارمزد)**\n\n"
            "پیشنهاد ما استفاده از شبکه‌های زیر برای حداقل کارمزد است:\n\n"
            "🔹 **TRON (TRX):**\n`آدرس_شما_اینجا`\n\n"
            "🔹 **TON (Toncoin):**\n`آدرس_شما_اینجا`\n\n"
            "🔹 **Tether (USDT-TRC20):**\n`آدرس_شما_اینجا`\n\n"
            "⚠️ پس از واریز، فقط **TXID** را اینجا ارسال کنید."
        ),
        'invoice_msg': "🧾 **فاکتور خرید**\n📌 پلن: {plan}\n💵 مبلغ: {price} تومان\n\nلطفاً پرداخت را انجام داده و TXID را بفرستید:",
        'tx_received': "✅ تراکنش ثبت شد. پس از تایید ادمین، سرویس ارسال و پورسانت معرف واریز می‌گردد.",
        'admin_panel': "🛠 **پنل مدیریت نُوا**\nیکی از گزینه‌های زیر را انتخاب کنید:",
        'sales_closed': "❌ متأسفانه در حال حاضر فروش موقتاً غیرفعال است."
    },
    'en': {
        'intro': (
            "🚀 **Welcome to Nova VPN**\n\n"
            "We provide the fastest and most secure internet infrastructure.\n\n"
            "💎 **Why Nova?**\n"
            "🔹 Dedicated 10Gbps servers\n"
            "🔹 No drops during peak hours\n"
            "🔹 Real 24/7 Support\n"
            "🔹 Compatible with all devices\n\n"
            "📢 **Channel:** @NovaVPN_Net\n"
            "🎧 **Support:** @NovaVPN_Sup\n\n"
            "👇 **Please select your language:**"
        ),
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
            "💰 **Wallet (Low Fees)**\n\n"
            "We recommend using these networks for the lowest transaction fees:\n\n"
            "🔹 **TRON (TRX):**\n`YOUR_ADDRESS_HERE`\n\n"
            "🔹 **TON (Toncoin):**\n`YOUR_ADDRESS_HERE`\n\n"
            "🔹 **Tether (USDT-TRC20):**\n`YOUR_ADDRESS_HERE`\n\n"
            "⚠️ Send the **TXID** after payment."
        ),
        'invoice_msg': "🧾 **Invoice**\n📌 Plan: {plan}\n💵 Price: {price} T\n\nPlease pay and send TXID:",
        'tx_received': "✅ TX submitted. Service will be sent after admin approval.",
        'admin_panel': "🛠 **Nova Admin Panel**",
        'sales_closed': "❌ Sales are temporarily disabled."
    }
}

# ==========================================
# 🛠 توابع کمکی
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
    if str(user['chat_id']) == ADMIN_ID: markup.row("🛠 Admin Panel")
    return markup

# ==========================================
# 🤖 هندلرهای اصلی
# ==========================================

@bot.message_handler(commands=['start'])
def start_cmd(message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    
    # لاجیک رفرال
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
        
        # آپدیت تعداد زیرمجموعه برای معرف
        if ref_id:
            requests.rpc('increment_referral', {'uid': ref_id}) # نیاز به فانکشن RPC در سوپابیس یا Patch ساده
            requests.patch(f"{URL}/rest/v1/users?chat_id=eq.{ref_id}", headers=DB_HEADERS, json={}) # در اینجا ساده نگه میداریم

        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa"),
                   telebot.types.InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"))
        bot.send_message(chat_id, STRINGS['fa']['intro'], reply_markup=markup, parse_mode="Markdown")
    else:
        lang = user.get('language', 'fa')
        bot.send_message(chat_id, STRINGS[lang]['welcome'], reply_markup=build_main_menu(user), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('setlang_'))
def callback_lang(call):
    chat_id = call.message.chat.id
    new_lang = call.data.split('_')[1]
    requests.patch(f"{URL}/rest/v1/users?chat_id=eq.{chat_id}", headers=DB_HEADERS, json={'language': new_lang})
    bot.delete_message(chat_id, call.message.message_id)
    user = get_user(chat_id)
    bot.send_message(chat_id, STRINGS[new_lang]['welcome'], reply_markup=build_main_menu(user))

# ==========================================
# 🛒 سیستم خرید و پورسانت
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
    
    if not plan['is_active']:
        bot.answer_callback_query(call.id, STRINGS[lang]['sales_closed'], show_alert=True)
        return

    text = STRINGS[lang]['invoice_msg'].format(plan=plan['title_fa'], price=plan['price_toman'])
    requests.post(f"{URL}/rest/v1/transactions", headers=DB_HEADERS, json={
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
    res = requests.patch(update_url, headers=DB_HEADERS, json={'txid_or_receipt': txid})
    
    if res.status_code < 300:
        bot.send_message(chat_id, STRINGS[user['language']]['tx_received'])
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_{txid}"),
                   telebot.types.InlineKeyboardButton("❌ رد", callback_data=f"reject_{txid}"))
        bot.send_message(ADMIN_ID, f"💰 تراکنش جدید!\nID: `{chat_id}`\nTXID: `{txid}`", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_', 'reject_')))
def admin_action(call):
    action, txid = call.data.split('_')
    if action == 'approve':
        tx = requests.get(f"{URL}/rest/v1/transactions?txid_or_receipt=eq.{txid}", headers=DB_HEADERS).json()[0]
        config = requests.get(f"{URL}/rest/v1/configs?plan_name=eq.{tx['target_plan']}&status=eq.available&limit=1", headers=DB_HEADERS).json()
        
        if config:
            conf = config[0]
            # تایید تراکنش و فروش کانفیگ
            requests.patch(f"{URL}/rest/v1/configs?id=eq.{conf['id']}", headers=DB_HEADERS, json={'status': 'sold', 'owner_id': tx['chat_id']})
            requests.patch(f"{URL}/rest/v1/transactions?id=eq.{tx['id']}", headers=DB_HEADERS, json={'status': 'approved'})
            
            # 🎁 محاسبه پورسانت ۱۰ درصدی برای معرف
            user = get_user(tx['chat_id'])
            if user['referrer_id']:
                commission = int(tx['amount_toman'] * 0.1)
                ref_user = get_user(user['referrer_id'])
                new_balance = ref_user['wallet_balance'] + commission
                requests.patch(f"{URL}/rest/v1/users?chat_id=eq.{user['referrer_id']}", headers=DB_HEADERS, json={'wallet_balance': new_balance})
                bot.send_message(user['referrer_id'], f"🎊 پورسانت واریز شد!\nمبلغ `{commission}` تومان بابت خرید زیرمجموعه شما به کیف پولتان اضافه شد.")

            bot.send_message(tx['chat_id'], f"🎉 تایید شد!\nکانفیگ:\n`{conf['v2ray_uri']}`\n[پنل حجم]({conf['web_panel_url']})", parse_mode="Markdown")
            bot.edit_message_text(f"✅ تایید شد: {txid}", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "انبار خالی است!", show_alert=True)
    else:
        bot.edit_message_text(f"❌ رد شد: {txid}", call.message.chat.id, call.message.message_id)

# ==========================================
# 🛠 پنل مدیریت (Admin Panel)
# ==========================================

@bot.message_handler(func=lambda m: m.text == "🛠 Admin Panel")
def admin_menu(message):
    if str(message.chat.id) != ADMIN_ID: return
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(telebot.types.InlineKeyboardButton("📦 مدیریت پلن‌ها", callback_data="admin_manage_plans"))
    markup.row(telebot.types.InlineKeyboardButton("📊 آمار کلی", callback_data="admin_stats"))
    bot.send_message(message.chat.id, STRINGS['fa']['admin_panel'], reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_callbacks(call):
    if call.data == "admin_manage_plans":
        plans = requests.get(f"{URL}/rest/v1/plans?select=*", headers=DB_HEADERS).json()
        markup = telebot.types.InlineKeyboardMarkup()
        for p in plans:
            status = "✅" if p['is_active'] else "❌"
            markup.row(telebot.types.InlineKeyboardButton(f"{status} {p['title_fa']} ({p['price_toman']})", callback_data=f"toggle_plan_{p['internal_name']}"))
        bot.edit_message_text("وضعیت فروش را تغییر دهید:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif call.data.startswith("toggle_plan_"):
        p_name = call.data.replace("toggle_plan_", "")
        current = requests.get(f"{URL}/rest/v1/plans?internal_name=eq.{p_name}", headers=DB_HEADERS).json()[0]
        requests.patch(f"{URL}/rest/v1/plans?internal_name=eq.{p_name}", headers=DB_HEADERS, json={'is_active': not current['is_active']})
        bot.answer_callback_query(call.id, "تغییر اعمال شد.")
        admin_callbacks(telebot.types.CallbackQuery(id=call.id, from_user=call.from_user, message=call.message, data="admin_manage_plans", chat_instance=call.chat_instance, json=None))

# ==========================================
# 🔘 هندلرهای دکمه‌های منو
# ==========================================

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
            markup.row(telebot.types.InlineKeyboardButton(f"{p['title_fa']} - {p['price_toman']} T", callback_data=f"buy_{p['internal_name']}"))
        bot.send_message(chat_id, s['buy_title'], reply_markup=markup, parse_mode="Markdown")
        
    elif message.text == s['btn_dash']:
        services = requests.get(f"{URL}/rest/v1/configs?owner_id=eq.{chat_id}&select=*", headers=DB_HEADERS).json()
        srv_text = "\n".join([f"🔹 {s['plan_name']} | [پنل]({s['web_panel_url']})" for s in services]) if services else "سرویسی ندارید."
        bot.send_message(chat_id, s['dash_title'].format(chat_id=chat_id, balance=user['wallet_balance'], services=srv_text), parse_mode="Markdown")
        
    elif message.text == s['btn_wallet']:
        bot.send_message(chat_id, s['wallet_title'], parse_mode="Markdown")
        
    elif message.text == s['btn_affiliate']:
        bot_un = bot.get_me().username
        bot.send_message(chat_id, s['affiliate_title'].format(bot_username=bot_un, chat_id=chat_id), parse_mode="Markdown")
        
    elif message.text == s['btn_support']:
        bot.send_message(chat_id, s['support_msg'])

# ==========================================
# 🌐 Flask Routes
# ==========================================

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
