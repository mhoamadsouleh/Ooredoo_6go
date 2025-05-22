import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import requests
import re
from datetime import datetime

BOT_TOKEN = "7723535106:AAH_8dQhq7QwVWh5JZf2iTrW4pgrT7vIykQ"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أرسل رقمك بدون 213، مثال: 773260982")

async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    number = update.message.text.strip()
    if not number.isdigit() or len(number) != 9:
        await update.message.reply_text("❌ الرقم غير صحيح، لازم يكون 9 أرقام.")
        return

    msisdn = "213" + number
    user_sessions[update.message.from_user.id] = {"msisdn": msisdn}

    data = {
        "msisdn": msisdn,
        "client_id": "6E6CwTkp8H1CyQxraPmcEJPQ7xka",
        "scope": "smsotp"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Djezzy/2.6.6"
    }

    r = requests.post("https://apim.djezzy.dz/oauth2/registration", data=data, headers=headers).text
    if "confirmation code has been sent" in r:
        await update.message.reply_text("✅ تم إرسال الرمز. أرسله هكذا:\n/otp 123456")
    else:
        await update.message.reply_text("❌ فشل إرسال الرمز. حاول مجددًا.")

async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("❌ اكتب الرمز هكذا:\n/otp 123456")
        return

    user_id = update.message.from_user.id
    if user_id not in user_sessions:
        await update.message.reply_text("❗ أرسل رقمك أولاً.")
        return

    otp = args[0]
    msisdn = user_sessions[user_id]["msisdn"]

    data = {
        "otp": otp,
        "mobileNumber": msisdn,
        "scope": "openid",
        "client_id": "6E6CwTkp8H1CyQxraPmcEJPQ7xka",
        "client_secret": "MVpXHW_ImuMsxKIwrJpoVVMHjRsa",
        "grant_type": "mobile"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Djezzy/2.6.6"
    }

    res = requests.post("https://apim.djezzy.dz/oauth2/token", data=data, headers=headers).json()
    token = res.get("access_token")
    if not token:
        await update.message.reply_text("❌ رمز OTP غير صالح.")
        return

    json_data = {
        "data": {
            "id": "GIFTWALKWIN",
            "type": "products",
            "meta": {
                "services": {
                    "steps": 10666,
                    "code": "GIFTWALKWIN2GO",
                    "id": "WALKWIN"
                }
            }
        }
    }

    r = requests.post(
        f"https://apim.djezzy.dz/djezzy-api/api/v1/subscribers/{msisdn}/subscription-product?include=",
        json=json_data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    ).text

    if "successfully done" in r:
        await update.message.reply_text("✅ تم الاشتراك في العرض بنجاح!")
    elif "nextEligibilityDate" in r:
        match = re.search(r'"nextEligibilityDate":"([^"]+)"', r)
        if match:
            next_time = datetime.fromisoformat(match.group(1))
            diff = next_time - datetime.now()
            await update.message.reply_text(f"⏳ مازال {diff.days} يوم و {diff.seconds//3600} ساعة باش تعاود تسجل.")
        else:
            await update.message.reply_text("⚠️ لا يمكنك الاشتراك الآن.")
    else:
        await update.message.reply_text("❌ فشل غير متوقع:\n" + r)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("otp", handle_otp))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))
    print("✅ البوت شغال على Render...")
    app.run_polling()

if __name__ == "__main__":
    main()
