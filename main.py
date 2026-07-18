import telebot
import random
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import os

# 1. 🔑 ضع توكن البوت الجديد هنا
BOT_TOKEN = "8990766814:AAHj-H3Ug3fbTVtqiGvrwgI49dOiW-eZOkA"
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

@app.route('/')
def home():
    return "بوت النشر التلقائي يعمل بنجاح!"

# 2. 📺 أرقام القنوات الخاصة بك
PRIVATE_CHANNEL = -1004495050725  # قناة المخزن السري
PUBLIC_CHANNEL = -1004102734458   # قناة الإعلانات العامة

# 3. 📦 قائمة المنشورات (البلونات والنصوص)
# كل قوسين يمثلون منشور: [رقم أول رسالة في البلونة, رقم الرسالة النصية اللي تحتها]
# إذا ضفت مقاطع جديدة مستقبلاً، بس أضف أرقامها هنا عشان البوت يسحبها بشكل صحيح
POSTS = [
    [2, 3],    # المنشور الأول
    [4, 5],    # المنشور الثاني 
    # [6, 7],  # تقدر تضيف المنشورات الجديدة بهذي الطريقة
]

def send_random_clip():
    print("🔍 جاري اختيار منشور عشوائي للنشر...")
    
    # اختيار منشور عشوائي من القائمة
    selected_post = random.choice(POSTS)
    start_id = selected_post[0]
    end_id = selected_post[1]
    
    # إنشاء قائمة بجميع أرقام الرسائل لهذا المنشور لنسخها كدفعة واحدة
    msg_ids = list(range(start_id, end_id + 1))
    
    try:
        # 🚀 السر هنا: copy_messages تنسخ البلونة والنص معاً بدون كلمة "محول من"
        bot.copy_messages(
            chat_id=PUBLIC_CHANNEL,
            from_chat_id=PRIVATE_CHANNEL,
            message_ids=msg_ids
        )
        print(f"✅ تم بنجاح نشر المنشور المكون من الرسائل: {msg_ids}")
    except Exception as e:
        print(f"❌ حدث خطأ أثناء النشر: {e}")

# 4. ⏰ ضبط توقيت الحملة (بتوقيت الرياض)
scheduler = BackgroundScheduler(timezone="Asia/Riyadh")

# الفترة الأولى: من 12:00 منتصف الليل وحتى 12:50 الليل
scheduler.add_job(send_random_clip, 'cron', hour=16, minute='24,10,20,30,40,50')

# الفترة الثانية: من 1:00 بعد منتصف الليل وحتى 1:30 الليل
scheduler.add_job(send_random_clip, 'cron', hour=16, minute='50,10,20,30')

scheduler.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
