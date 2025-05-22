import os
import requests
from uuid import uuid4
import telebot
import time
import sqlite3
import random

TOKEN = "8155271835:AAHoCTwDe5laiIRFiQerj7EKRygg1JHDOkA"
bot = telebot.TeleBot(TOKEN)

# إعداد قاعدة البيانات
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (phone TEXT PRIMARY KEY, token TEXT)")
conn.commit()

def generate_user_agent():
    agents = [
        "Mozilla/5.0 (Linux; Android 10; SM-G975F)",
        "Mozilla/5.0 (Linux; Android 11; Pixel 4 XL)",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)",
    ]
    return random.choice(agents)

welcome_message = (
    "مرحبًا بك!\n\n"
    "أرسل رقم هاتفك (مثال: 05xxxxxxxx) لتفعيل الإنترنت."
)

# يتحقق إذا الرقم يحتاج OTP أو لا
def check_requires_otp(phone_number):
    try:
        headers = {
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
        # إذا فيها OTP معناها لازم الرمز
        if "otp" in response.text.lower():
            return True
        elif "access_token" in response.text:
            return False
        else:
            return None
    except:
        return None

# تحقق من رمز OTP وأرجع التوكن
def verify_otp(phone_number, otp):
    headers = {
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
        'Authorization': f'Bearer {access_token}',
        'User-Agent': generate_user_agent(),
    }
    try:
        json_data = {'mgmValue': '6GB'}
        requests.post(
            'https://apis.ooredoo.dz/api/ooredoo-bff/users/mgm/info/apply',
            headers=headers,
            json=json_data,
        )
        time.sleep(4)
        requests.put(
            'https://apis.ooredoo.dz/api/ooredoo-bff/users/mgm/redeem',
            headers=headers,
        )
    except:
        pass

def get_balance(access_token):
    headers = {
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
        return

    if message.text.startswith("05") and len(message.text) == 10:
        phone_number = message.text[1:]

        cursor.execute("SELECT token FROM users WHERE phone = ?", (phone_number,))
        result = cursor.fetchone()

        if result:
            access_token = result[0]
            bot.send_message(message.chat.id, "✅ مرحبًا مجددًا، جاري تفعيل الإنترنت...")
            activate_internet(access_token)
            balance, phone = get_balance(access_token)
            bot.send_message(message.chat.id, f"✅ تم التفعيل.\nرصيدك: {balance} دج\nرقمك: {phone}")
        else:
            bot.send_message(message.chat.id, "⏳ جاري التحقق من حالتك...")
            needs_otp = check_requires_otp(phone_number)

            if needs_otp is None:
                bot.send_message(message.chat.id, "❌ حدث خطأ. تأكد من اتصالك أو افتح تطبيق My Ooredoo.")
            elif needs_otp:
                bot.send_message(message.chat.id, "📩 تم إرسال رمز التحقق، أكتبه الآن.")
                bot.register_next_step_handler(message, process_otp, phone_number)
            else:
                # الرقم لا يحتاج OTP، نأخذ التوكن مباشرة
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'User-Agent': generate_user_agent(),
                }
                data = {
                    'grant_type': 'password',
                    'username': f'213{phone_number}',
                    'client_id': 'myooredoo-app',
                }
                try:
                    response = requests.post(
                        'https://apis.ooredoo.dz/api/auth/realms/myooredoo/protocol/openid-connect/token',
                        headers=headers,
                        data=data,
                    ).json()
                    access_token = response.get("access_token")
                    if access_token:
                        cursor.execute("INSERT INTO users (phone, token) VALUES (?, ?)", (phone_number, access_token))
                        conn.commit()
                        bot.send_message(message.chat.id, "✅ تم تسجيلك بنجاح، جاري تفعيل الإنترنت...")
                        activate_internet(access_token)
                        balance, phone = get_balance(access_token)
                        bot.send_message(message.chat.id, f"✅ تم التفعيل.\nرصيدك: {balance} دج\nرقمك: {phone}")
                    else:
                        bot.send_message(message.chat.id, "❌ لم نتمكن من تسجيل الدخول.")
                except:
                    bot.send_message(message.chat.id, "❌ خطأ في الاتصال.")
    else:
        bot.send_message(message.chat.id, welcome_message)

def process_otp(message, phone_number):
    otp = message.text.strip()
    bot.send_message(message.chat.id, "⏳ جارٍ التحقق من الرمز...")
    access_token = verify_otp(phone_number, otp)
    if access_token:
        cursor.execute("INSERT INTO users (phone, token) VALUES (?, ?)", (phone_number, access_token))
        conn.commit()
        bot.send_message(message.chat.id, "✅ تم التحقق، جاري تفعيل الإنترنت...")
        activate_internet(access_token)
        balance, phone = get_balance(access_token)
        bot.send_message(message.chat.id, f"✅ تم التفعيل.\nرصيدك: {balance} دج\nرقمك: {phone}")
    else:
        bot.send_message(message.chat.id, "❌ رمز تحقق خاطئ أو منتهي. حاول مجددًا.")

bot.polling(none_stop=True)
