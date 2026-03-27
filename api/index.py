import os
import telebot
import requests
import traceback
from flask import Flask, request

app = Flask(__name__)

# =========================
# ENV
# =========================
TOKEN = os.environ.get("TELEGRAM_TOKEN")
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
ADMIN_ID = str(os.environ.get("ADMIN_CHAT_ID"))

bot = telebot.TeleBot(
    TOKEN,
    threaded=True,
    num_threads=60
)

db = requests.Session()

DB_HEADERS = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# =========================
# CACHE
# =========================
USER_CACHE = {}

# =========================
# STRINGS SAFE
# =========================
STRINGS = {
    "fa": {
        "btn_buy": "🛒 خرید",
        "btn_wallet": "💰 کیف پول",
        "btn_dash": "👤 داشبورد",
        "btn_support": "🎧 پشتیبانی",
        "error": "⚠️ خطا رخ داد دوباره تلاش کنید"
    }
}

# =========================
# USER
# =========================
def get_user(chat_id):

    if chat_id in USER_CACHE:
        return USER_CACHE[chat_id]

    try:
        r = db.get(
            f"{URL}/rest/v1/users?chat_id=eq.{chat_id}&select=*",
            headers=DB_HEADERS,
            timeout=2
        )

        data = r.json()

        if data:
            USER_CACHE[chat_id] = data[0]
            return data[0]

        new = {
            "chat_id": chat_id,
            "role": "admin" if str(chat_id) == ADMIN_ID else "user",
            "balance": 0
        }

        r = db.post(
            f"{URL}/rest/v1/users",
            headers=DB_HEADERS,
            json=new,
            timeout=2
        )

        user = r.json()[0]
        USER_CACHE[chat_id] = user
        return user

    except:
        return None


# =========================
# MENU
# =========================
def menu():
    m = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    s = STRINGS["fa"]

    m.row(s["btn_buy"])
    m.row(s["btn_dash"], s["btn_wallet"])
    m.row(s["btn_support"])

    return m


# =========================
# START
# =========================
@bot.message_handler(commands=["start"])
def start(message):

    try:
        user = get_user(message.chat.id)

        bot.send_message(
            message.chat.id,
            "🚀 ربات نُوا فعال شد",
            reply_markup=menu()
        )

    except Exception as e:
        print(traceback.format_exc())


# =========================
# BUY
# =========================
@bot.message_handler(func=lambda m: m.text == STRINGS["fa"]["btn_buy"])
def buy(message):

    try:
        bot.send_message(
            message.chat.id,
            "🛒 لیست پلن ها بزودی..."
        )
    except:
        bot.send_message(message.chat.id, STRINGS["fa"]["error"])


# =========================
# WALLET
# =========================
@bot.message_handler(func=lambda m: m.text == STRINGS["fa"]["btn_wallet"])
def wallet(message):

    try:
        user = get_user(message.chat.id)

        bot.send_message(
            message.chat.id,
            f"💰 موجودی شما: {user.get('balance',0)}"
        )

    except:
        bot.send_message(message.chat.id, STRINGS["fa"]["error"])


# =========================
# TEXT FALLBACK
# =========================
@bot.message_handler(content_types=["text"])
def text_handler(message):

    try:
        if not message.text:
            return

        bot.send_message(
            message.chat.id,
            "❓ دستور نامعتبر"
        )

    except:
        pass


# =========================
# WEBHOOK
# =========================
@app.route("/", methods=["POST"])
def webhook():

    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200

    return "Bad", 403
