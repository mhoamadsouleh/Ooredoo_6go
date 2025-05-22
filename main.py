import os
import requests
from uuid import uuid4
import telebot
import time
import sqlite3
import random

TOKEN = "8155271835:AAHoCTwDe5laiIRFiQerj7EKRygg1JHDOkA"

bot = telebot.TeleBot(TOKEN)

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (phone TEXT PRIMARY KEY, token TEXT)")
conn.commit()

def generate_user_agent():
    agents = [
        "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 Chrome/91.0.4472.114 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 11; Pixel 4 XL) AppleWebKit/537.36 Chrome/91.0.4472.114 Mobile Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
    ]
    return random.choice(agents)

welcome_message = (
    "مرحبًا بك معنا 💜!\n\n"
    "بوت Flexy تفعيل الإنترنت بسهولة وسرعة 🚀.\n\n"
    "كل ما عليك هو إرسال رقم الهاتف الخاص بك مع إدخال رمز التحقق.\n"
    "لنبدأ الآن! 📱"
)

def send_otp(phone_number):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': generate_user_agent(),
    }
    data = {
        'grant_type': 'password',
        'username': f'213{phone_number}',
        'client_id': 'myooredoo-app',
    }
    response = requests.post(
        'https://apis.ooredoo.dz/api/auth/realms/myooredoo/protocol/openid-connect/token',
        headers=headers,
        data=data,
    )
    return response.status_code == 403

def verify_otp(phone_number, otp):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': generate_user_agent(),
        'X-Correlation-ID': str(uuid4()),
    }
    data = {
        'grant_type': 'password',
        'username': f'213{phone_number}',
        'client_id': 'myooredoo-app',
        'otp': otp,
    }
    try:
        response = requests.post(
            'https://apis.ooredoo.dz/api/auth/realms/myooredoo/protocol/openid-connect/token',
            headers=headers,
            data=data,
        ).json()
        return response.get("access_token")
    except:
        return None

def activate_internet(access_token):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Authorization': f'Bearer {access_token}',
        'User-Agent': generate_user_agent(),
    }
    json_data = {'mgmValue': '6GB'}
    requests.post(
        'https://apis.ooredoo.dz/api/ooredoo-bff/users/mgm/info/apply',
        headers=headers,
        json=json_data,
    )
    time.sleep(5)
    requests.put(
        'https://apis.ooredoo.dz/api/ooredoo-bff/users/mgm/redeem',
        headers=headers,
    )

def get_balance(access_token):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Authorization': f'Bearer {access_token}',
        'User-Agent': generate_user_agent(),
    }
    try:
        response = requests.get(
            'https://apis.ooredoo.dz/api/ooredoo-bff/subscriptions/getAccountInfo',
            headers=headers,
        ).json()
        return response.get('accountBalance'), response.get('msisdn')
    except:
        return None, None

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.chat.type != 'private':
        bot.send_message(message.chat.id, "❌ هذا البوت يعمل في الخاص فقط.")
        return

    if message.text.startswith("05") and len(message.text) == 10:
        phone_number = message.text[1:]

        cursor.execute("SELECT token FROM users WHERE phone = ?", (phone_number,))
        result = cursor.fetchone()

        if result:
            access_token = result[0]
            bot.send_message(message.chat.id, "✅ تم تسجيل الدخول. يتم الآن تفعيل الإنترنت...")
            activate_internet(access_token)
            balance, phone = get_balance(access_token)
            msg = f"✅ تم التفعيل.\nرصيدك: {balance} دج.\nرقمك: {phone}"
            bot.send_message(message.chat.id, msg)
        else:
            bot.send_message(message.chat.id, "جاري إرسال رمز التحقق...")
            if send_otp(phone_number):
                bot.send_message(message.chat.id, "✅ تم إرسال الرمز. أدخل رمز التحقق.")
                bot.register_next_step_handler(message, process_otp, phone_number)
            else:
                bot.send_message(message.chat.id, "تعذر الإرسال. جرب فتح تطبيق My Ooredoo ثم أعد المحاولة.")
    else:
        bot.send_message(message.chat.id, welcome_message)

def process_otp(message, phone_number):
    otp = message.text
    bot.send_message(message.chat.id, "جارٍ التحقق من الرمز...")
    access_token = verify_otp(phone_number, otp)
    if access_token:
        cursor.execute("INSERT INTO users (phone, token) VALUES (?, ?)", (phone_number, access_token))
        conn.commit()
        bot.send_message(message.chat.id, "✅ تم التحقق. جارٍ التفعيل...")
        activate_internet(access_token)
        balance, phone = get_balance(access_token)
        msg = f"✅ تم التفعيل.\nرصيدك: {balance} دج.\nرقمك: {phone}"
        bot.send_message(message.chat.id, msg)
    else:
        bot.send_message(message.chat.id, "❌ رمز تحقق خاطئ. حاول مرة أخرى.")

bot.polling(none_stop=True)
