import telebot
import random
import threading
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import os

BOT_TOKEN = "8990766814:AAHj-H3Ug3fbTVtqiGvrwgI49dOiW-eZOkA"
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

PRIVATE_CHANNEL = -1004495050725
PUBLIC_CHANNEL = -1004102734458

# قائمة المنشورات
POSTS = []

# متغيرات التجميع التلقائي
pending_messages = []
timer = None

def save_new_post():
    global pending_messages, POSTS
    if pending_messages:
        pending_messages.sort()
        POSTS.append(pending_messages.copy())
        print(f"✅ تم اكتشاف وحفظ منشور جديد آلياً: {pending_messages}")
        pending_messages.clear()

@bot.channel_post_handler(func=lambda message: message.chat.id == PRIVATE_CHANNEL)
def catch_new_posts(message):
    global pending_messages, timer
    pending_messages.append(message.message_id)
    if timer is not None:
        timer.cancel()
    timer = threading.Timer(3.0, save_new_post)
    timer.start()

def send_random_clip():
    if not POSTS:
        print("⚠️ لا يوجد منشورات في الذاكرة حالياً. أرسل منشوراً جديداً للقناة!")
        return
        
    selected_post = random.choice(POSTS)
    try:
        bot.forward_messages(
            chat_id=PUBLIC_CHANNEL,
            from_chat_id=PRIVATE_CHANNEL,
            message_ids=selected_post
        )
        print(f"🚀 تم النشر بنجاح: {selected_post}")
    except Exception as e:
        print(f"❌ حدث خطأ أثناء النشر: {e}")

# ضبط التوقيت: النشر عند 17:30 و 17:45
scheduler = BackgroundScheduler(timezone="Asia/Riyadh")
scheduler.add_job(send_random_clip, 'cron', hour=17, minute='30,35')
scheduler.start()

def run_bot():
    print("🤖 البوت يعمل الآن.. بانتظار منشوراتك للنشر في 17:30 و 17:45.")
    bot.infinity_polling()

@app.route('/')
def home():
    return f"البوت يعمل! المنشورات المحفوظة: {len(POSTS)}"

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
