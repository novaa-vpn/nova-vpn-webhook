import os
import telebot
import requests
import traceback
from flask import Flask, request

app = Flask(__name__)

# ==========================================
# 🔐 تنظیمات و متغیرهای محیطی
# ==========================================
TOKEN = os.environ.get('TELEGRAM_TOKEN', '').strip()
URL = os.environ.get('SUPABASE_URL', '').strip()
KEY = os.environ.get('SUPABASE_KEY', '').strip()
ADMIN_ID = os.environ.get('ADMIN_CHAT_ID', '').strip()
BOT_USERNAME = "NoovaVpn_Bot"

# استفاده از Session جهانی برای حذف زمان Handshake در هر درخواست
db_session = requests.Session()
bot = telebot.TeleBot(TOKEN, threaded=True)

# هدرهای بهینه‌شده برای دریافت مستقیم نتیجه پس از درج/ویرایش (کاهش یک مرحله درخواست)
DB_HEADERS = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ==========================================
# 🛠 توابع کمکی فوق سریع
# ==========================================

def f_price(amount):
    """جداکننده ۳ رقم ۳ رقم اعداد برای نمایش حرفه‌ای"""
    try:
        return f"{int(amount or 0):,}"
    except:
        return str(amount or 0)

def get_or_create_user(message):
    """
    ادغام عملیات بررسی و ثبت‌نام در یک مرحله (کاهش Latency)
    """
    chat_id = message.chat.id
    try:
        # ابتدا سعی می‌کنیم اطلاعات را بگیریم
        res = db_session.get(f"{URL}/rest/v1/users?chat_id=eq.{chat_id}&select=*", headers=DB_HEADERS, timeout=4)
        data = res.json()
        
        if data and isinstance(data, list) and len(data) > 0:
            return data[0]
        
        # اگر کاربر نبود، ثبت‌نام می‌کنیم
        ref_id = None
        if hasattr(message, 'text') and message.text and len(message.text.split()) > 1:
            potential_ref = message.text.split()[1]
            if potential_ref.isdigit() and int(potential_ref) != chat_id:
                ref_id = int(potential_ref)

        role = 'admin' if str(chat_id) == ADMIN_ID else 'user'
        new_user = {
            'chat_id': chat_id, 
            'username': message.from_user.username,
            'role': role, 
            'language': 'fa', 
            'referrer_id': ref_id
        }
        
        # ثبت و دریافت آنی اطلاعات (بدون نیاز به Get دوباره)
        post_res = db_session.post(f"{URL}/rest/v1/users", headers=DB_HEADERS, json=new_user, timeout=4)
        return post_res.json()[0] if post_res.json() else None
    except Exception as e:
        print(f"❌ DB Error: {e}")
        return None

def build_main_menu(user):
    lang = user.get('language', 'fa')
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    s = STRINGS.get(lang, STRINGS['fa'])
    
    markup.row(s['btn_buy'])
    markup.row(s['btn_dash'], s['btn_wallet'])
    markup.row(s['btn_affiliate'], s['btn_support'])
    markup.row(s['btn_lang'])
    
    if str(user.get('chat_id')) == ADMIN_ID:
        markup.row("🛠 Admin Panel")
    return markup

# ==========================================
# 📝 دیکشنری متون دوزبانه نُوا
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
        'welcome': "💎 **نُوا با موفقیت فعال شد!**\nهم‌اکنون از منوی زیر استفاده کنید.",
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
            "🔹 **TRX / USDT (TRC20):**\n`TSgfCoCsrEXJs6RKkaCJF64wXpYVTRejZ3`\n\n"
            "🔹 **TON (Toncoin):**\n`UQCpWdG73bwuwFAp2EDQLLkl6VhTGpVVJDre8X02qvJ5OJem`\n\n"
            "🔹 **Ripple (XRP):**\n`rJ8A6gUZzwXm9XJv2fLaTGd6GkpBMdmm8F`\n\n"
            "⚠️ پس از واریز، فقط **هش تراکنش (TXID)** را در اینجا ارسال کنید."
        ),
        'invoice_msg': "🧾 **فاکتور خرید**\n📌 پلن: {plan}\n💵 مبلغ: {price} تومان\n\nلطفاً مبلغ را واریز و TXID را بفرستید:",
        'tx_received': "✅ تراکنش با موفقیت ثبت شد و در صف تایید قرار گرفت.",
        'support_msg': "🎧 جهت ارتباط با پشتیبانی: @NovaVPN_Sup",
        'lang_set': "زبان با موفقیت به فارسی تغییر کرد. 🇮🇷",
        'no_services': "شما اشتراک فعالی ندارید."
    },
    'en': {
        'intro': "🚀 **Welcome to Nova VPN**\n\nPlease select your language to start:",
        'welcome': "💎 **Nova is ready!**",
        'main_menu': "🏠 **Menu**\n➖➖➖➖➖➖\n💰 Balance: `{balance}` T\n👥 Referrals: `{ref_count}`",
        'btn_buy': "🛒 Buy VIP Plan",
        'btn_dash': "👤 My Dashboard",
        'btn_wallet': "💰 Wallet / Top-up",
        'btn_affiliate': "🤝 Affiliate",
        'btn_support': "🎧 Support",
        'btn_lang': "🌐 تغییر زبان",
        'dash_title': "👤 **Dashboard**\n\n🆔 ID: `{chat_id}`\n💰 Balance: `{balance}` T\n\n📦 **Services:**\n{services}",
        'wallet_title': "💰 **Wallet**\nSend TXID after payment to our addresses.",
        'invoice_msg': "🧾 **Invoice**\n📌 Plan: {plan}\n💵 Price: {price} T\n\nSend TXID:",
        'tx_received': "✅ TX received. Processing...",
        'support_msg': "🎧 Support: @NovaVPN_Sup",
        'lang_set': "Language set to English. 🇬🇧",
        'no_services': "No active services."
    }
}

# ==========================================
# 🤖 هندلرهای ربات
# ==========================================

@bot.message_handler(commands=['start'])
def start_cmd(message):
    try:
        user = get_or_create_user(message)
        if not user: return

        # اگر کاربر جدید است (زمان عضویت با زمان حال یکی باشد یا فیلد زبان خالی باشد)
        if not user.get('language') or user.get('total_referrals') == 0:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(telebot.types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa"),
                       telebot.types.InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"))
            bot.send_message(message.chat.id, STRINGS['fa']['intro'], reply_markup=markup, parse_mode="Markdown")
        else:
            lang = user.get('language', 'fa')
            text = STRINGS[lang]['main_menu'].format(balance=f_price(user.get('wallet_balance', 0)), ref_count=user.get('total_referrals', 0))
            bot.send_message(message.chat.id, text, reply_markup=build_main_menu(user), parse_mode="Markdown")
    except Exception as e:
        print(f"Error in start: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('setlang_'))
def callback_lang(call):
    try:
        chat_id = call.message.chat.id
        new_lang = call.data.split('_')[1]
        # آپدیت و دریافت نتیجه در یک مرحله
        res = db_session.patch(f"{URL}/rest/v1/users?chat_id=eq.{chat_id}", headers=DB_HEADERS, json={'language': new_lang}, timeout=4)
        bot.delete_message(chat_id, call.message.message_id)
        user = res.json()[0] if res.json() else None
        if user:
            bot.send_message(chat_id, STRINGS[new_lang]['welcome'], reply_markup=build_main_menu(user), parse_mode="Markdown")
    except Exception as e:
        print(f"Error in lang selection: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_buy_plan(call):
    try:
        chat_id = call.message.chat.id
        plan_name = call.data.split('_', 1)[1]
        # بهینه سازی: دریافت پلن در یک مرحله
        res = db_session.get(f"{URL}/rest/v1/plans?internal_name=eq.{plan_name}", headers=DB_HEADERS, timeout=4).json()
        if not res: return
        plan = res[0]
        
        # دریافت اطلاعات کاربر برای تشخیص زبان
        user_res = db_session.get(f"{URL}/rest/v1/users?chat_id=eq.{chat_id}", headers=DB_HEADERS, timeout=4).json()
        lang = user_res[0]['language'] if user_res else 'fa'
        
        if not plan['is_active']:
            bot.answer_callback_query(call.id, STRINGS[lang]['sales_closed'], show_alert=True)
            return

        text = STRINGS[lang]['invoice_msg'].format(plan=plan['title_fa'], price=f_price(plan['price_toman']))
        # ثبت تراکنش
        db_session.post(f"{URL}/rest/v1/transactions", headers=DB_HEADERS, json={
            'chat_id': chat_id, 'amount_toman': plan['price_toman'],
            'target_plan': plan_name, 'status': 'pending', 'txid_or_receipt': 'AWAITING'
        }, timeout=4)
        bot.edit_message_text(text, chat_id, call.message.message_id, parse_mode="Markdown")
    except Exception as e:
        print(f"Error in buy_plan: {e}")

@bot.message_handler(func=lambda m: m.text and len(m.text) > 20)
def handle_txid(message):
    try:
        chat_id = message.chat.id
        txid = message.text.strip()
        # آپدیت و تایید در یک مرحله
        res = db_session.patch(f"{URL}/rest/v1/transactions?chat_id=eq.{chat_id}&txid_or_receipt=eq.AWAITING", 
                               headers=DB_HEADERS, json={'txid_or_receipt': txid}, timeout=4)
        
        if res.status_code < 300:
            bot.send_message(chat_id, "✅ تراکنش ثبت شد. در حال بررسی توسط ادمین...", parse_mode="Markdown")
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(telebot.types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_{txid}"),
                       telebot.types.InlineKeyboardButton("❌ رد", callback_data=f"reject_{txid}"))
            bot.send_message(ADMIN_ID, f"💰 **تراکنش جدید!**\nکاربر: `{chat_id}`\nهش: `{txid}`", reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        print(f"Error in txid: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_', 'reject_')))
def admin_action(call):
    try:
        action, txid = call.data.split('_')
        if action == 'approve':
            tx_res = db_session.get(f"{URL}/rest/v1/transactions?txid_or_receipt=eq.{txid}", headers=DB_HEADERS, timeout=4).json()
            if not tx_res: return
            tx = tx_res[0]
            
            config_res = db_session.get(f"{URL}/rest/v1/configs?plan_name=eq.{tx['target_plan']}&status=eq.available&limit=1", headers=DB_HEADERS, timeout=4).json()
            
            if config_res:
                conf = config_res[0]
                # عملیات همزمان: فروش کانفیگ و تایید تراکنش
                db_session.patch(f"{URL}/rest/v1/configs?id=eq.{conf['id']}", headers=DB_HEADERS, json={'status': 'sold', 'owner_id': tx['chat_id']}, timeout=4)
                db_session.patch(f"{URL}/rest/v1/transactions?id=eq.{tx['id']}", headers=DB_HEADERS, json={'status': 'approved'}, timeout=4)
                
                # پورسانت رفرال
                buyer_res = db_session.get(f"{URL}/rest/v1/users?chat_id=eq.{tx['chat_id']}", headers=DB_HEADERS, timeout=4).json()
                if buyer_res and buyer_res[0]['referrer_id']:
                    ref_id = buyer_res[0]['referrer_id']
                    comm = int(tx['amount_toman'] * 0.1)
                    # آپدیت موجودی معرف
                    db_session.rpc('increment_wallet', {'user_id': ref_id, 'amount': comm}) # پیشنهاد: ساخت RPC در سوپابیس برای سرعت

                bot.send_message(tx['chat_id'], f"🎉 **سرویس فعال شد!**\n\n🚀 کانفیگ:\n`{conf['v2ray_uri']}`", parse_mode="Markdown")
                bot.edit_message_text(f"✅ تایید شد: `{txid}`", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            else:
                bot.answer_callback_query(call.id, "❌ انبار خالی است!", show_alert=True)
        else:
            bot.edit_message_text(f"❌ تراکنش رد شد: `{txid}`", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    except Exception as e:
        print(f"Error in admin action: {e}")

@bot.message_handler(func=lambda m: m.text == "🛠 Admin Panel")
def admin_menu(message):
    if str(message.chat.id) != ADMIN_ID: return
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(telebot.types.InlineKeyboardButton("📦 مدیریت پلن‌ها", callback_data="admin_manage_plans"))
    bot.send_message(message.chat.id, "🛠 **پنل مدیریت نُوا**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_callbacks(call):
    if str(call.message.chat.id) != ADMIN_ID: return
    if call.data == "admin_manage_plans":
        plans = db_session.get(f"{URL}/rest/v1/plans?select=*", headers=DB_HEADERS, timeout=4).json()
        markup = telebot.types.InlineKeyboardMarkup()
        for p in plans:
            status = "✅" if p['is_active'] else "❌"
            markup.row(telebot.types.InlineKeyboardButton(f"{status} | {p['title_fa']}", callback_data=f"toggle_plan_{p['internal_name']}"))
        bot.edit_message_text("تغییر وضعیت فروش:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif call.data.startswith("toggle_plan_"):
        p_name = call.data.replace("toggle_plan_", "")
        current = db_session.get(f"{URL}/rest/v1/plans?internal_name=eq.{p_name}", headers=DB_HEADERS, timeout=4).json()[0]
        db_session.patch(f"{URL}/rest/v1/plans?internal_name=eq.{p_name}", headers=DB_HEADERS, json={'is_active': not current['is_active']}, timeout=4)
        admin_callbacks(telebot.types.CallbackQuery(id=call.id, from_user=call.from_user, message=call.message, data="admin_manage_plans", chat_instance=call.chat_instance, json=None))

@bot.message_handler(func=lambda m: True)
def menu_logic(message):
    try:
        chat_id = message.chat.id
        user = get_or_create_user(message)
        if not user or not message.text: return
        
        lang = user.get('language', 'fa')
        text = message.text
        s = STRINGS.get(lang, STRINGS['fa'])
        
        if text == s['btn_buy']:
            plans = db_session.get(f"{URL}/rest/v1/plans?is_active=eq.true&select=*", headers=DB_HEADERS, timeout=4).json()
            if not plans: 
                bot.send_message(chat_id, s['sales_closed'])
                return
            markup = telebot.types.InlineKeyboardMarkup()
            for p in plans:
                markup.row(telebot.types.InlineKeyboardButton(f"{p['title_fa']} - {f_price(p['price_toman'])} T", callback_data=f"buy_{p['internal_name']}"))
            bot.send_message(chat_id, s['buy_title'], reply_markup=markup, parse_mode="Markdown")
            
        elif text == s['btn_dash']:
            # دریافت اطلاعات سرویس‌ها
            services = db_session.get(f"{URL}/rest/v1/configs?owner_id=eq.{chat_id}&select=*", headers=DB_HEADERS, timeout=4).json()
            srv_list = [f"🔹 {s['plan_name']} | [پنل]({s['web_panel_url']})" for s in services]
            srv_text = "\n".join(srv_list) if srv_list else s['no_services']
            bot.send_message(chat_id, s['dash_title'].format(chat_id=chat_id, balance=f_price(user['wallet_balance']), services=srv_text), parse_mode="Markdown", disable_web_page_preview=True)
            
        elif text == s['btn_wallet']:
            bot.send_message(chat_id, s['wallet_title'], parse_mode="Markdown")
            
        elif text == s['btn_affiliate']:
            bot.send_message(chat_id, s['affiliate_title'].format(bot_username=BOT_USERNAME, chat_id=chat_id), parse_mode="Markdown")
            
        elif text == s['btn_support']:
            bot.send_message(chat_id, s['support_msg'])
            
        elif text == s['btn_lang']:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(telebot.types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa"),
                       telebot.types.InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"))
            bot.send_message(chat_id, "Select Language / انتخاب زبان:", reply_markup=markup)
    except Exception as e:
        print(f"Error in menu: {e}")

# ==========================================
# 🌐 Flask Routes (Entry Point)
# ==========================================

@app.route('/', methods=['GET'])
def index():
    return "✅ Nova VPN Backend is Online!"

@app.route('/setup', methods=['GET'])
def setup():
    webhook_url = request.url_root.replace("http://", "https://") + TOKEN
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f"Webhook set to: {webhook_url}"

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        if request.headers.get('content-type') == 'application/json':
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            # پردازش پیام
            bot.process_new_updates([update])
            return 'OK', 200
    except Exception as e:
        print(f"🚨 Webhook Error: {e}")
    return 'OK', 200

if __name__ == "__main__":
    app.run()
