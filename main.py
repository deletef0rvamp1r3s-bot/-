import telebot
import random
import threading
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import os

BOT_TOKEN = "ضع_توكن_بوتك_الجديد_هنا"
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

PRIVATE_CHANNEL = -1004495050725
PUBLIC_CHANNEL = -1004102734458

# قائمة المنشورات أصبحت ديناميكية (البوت سيعبئها بنفسه)
POSTS = []

# متغيرات التجميع التلقائي
pending_messages = []
timer = None

def save_new_post():
    """دالة لجمع الرسائل التي وصلت معاً وحفظها كمنشور واحد"""
    global pending_messages, POSTS
    if pending_messages:
        # ترتيب الأرقام لضمان أن المقطع أولاً ثم النص
        pending_messages.sort()
        POSTS.append(pending_messages.copy())
        print(f"✅ تم اكتشاف وحفظ منشور جديد آلياً بالأرقام: {pending_messages}")
        pending_messages.clear()

@bot.channel_post_handler(func=lambda message: message.chat.id == PRIVATE_CHANNEL)
def catch_new_posts(message):
    """الاستماع للقناة السرية وجمع الرسائل المتتالية"""
    global pending_messages, timer
    
    pending_messages.append(message.message_id)
    
    # إلغاء العداد القديم وبدء عداد جديد لـ 3 ثواني
    # (ينتظر البوت ليرى هل هناك رسائل تابعة لنفس البوست كالنص مثلاً)
    if timer is not None:
        timer.cancel()
        
    timer = threading.Timer(3.0, save_new_post)
    timer.start()

def send_random_clip():
    """المسؤول عن النشر العشوائي في الأوقات المجدولة"""
    if not POSTS:
        print("⚠️ لا يوجد منشورات محفوظة في ذاكرة البوت حالياً.")
        return
        
    print("🔍 جاري اختيار منشور عشوائي للنشر...")
    selected_post = random.choice(POSTS)
    
    try:
        # استخدام forward_messages لنقل الألبوم كاملاً مع النص بالترتيب
        bot.forward_messages(
            chat_id=PUBLIC_CHANNEL,
            from_chat_id=PRIVATE_CHANNEL,
            message_ids=selected_post
        )
        print(f"✅ تم النشر بنجاح: {selected_post}")
    except Exception as e:
        print(f"❌ حدث خطأ أثناء النشر: {e}")

# إعداد توقيت الحملة
scheduler = BackgroundScheduler(timezone="Asia/Riyadh")
scheduler.add_job(send_random_clip, 'cron', hour=17, minute='3,6,20,30,40,50')
scheduler.add_job(send_random_clip, 'cron', hour=17, minute='20,30,20,30')
scheduler.start()

def run_bot():
    print("🤖 البوت يعمل الآن.. ينتظر منشوراتك الجديدة ويترقب وقت النشر.")
    bot.infinity_polling()

@app.route('/')
def home():
    return f"البوت يعمل! عدد المنشورات الجاهزة للنشر العشوائي: {len(POSTS)}"

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
