import telebot
import random
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import os
import json
import threading

# 1. 🔑 توكن البوت الخاص بك
BOT_TOKEN = "8990766814:AAFtq2VwLHe0nCqrndFj2ucff2fUrsiik9M"
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

# 2. 📺 أرقام القنوات (تأكد من وجود السالب قبل الرقم)
PRIVATE_CHANNEL = -1004495050725
PUBLIC_CHANNEL = -1004102734458

# 3. 🗂️ ملفات الذاكرة
DB_FILE = "database.json"
HISTORY_FILE = "history.json"
db_lock = threading.Lock()

# إنشاء الملفات إذا لم تكن موجودة
for file in [DB_FILE, HISTORY_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump([], f)

# دالة حفظ المنشور في قاعدة البيانات
def save_post_to_db(post_ids):
    with db_lock:
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
        except:
            data = []
        
        if post_ids not in data:
            data.append(post_ids)
            with open(DB_FILE, "w") as f:
                json.dump(data, f)
            print(f"💾 تم رصد وحفظ منشور جديد: {post_ids}")

# 📡 مستشعر القناة
@bot.channel_post_handler(func=lambda message: message.chat.id == PRIVATE_CHANNEL)
def auto_save_posts(message):
    # حفظ أي نوع من المنشورات (فيديو، صورة، نص)
    save_post_to_db([message.message_id])

# 🛠️ أمر فحص الذاكرة
@bot.message_handler(commands=['db'])
def check_db(message):
    try:
        with open(DB_FILE, "r") as f:
            data = f.read()
        bot.reply_to(message, f"📂 محتوى الذاكرة حالياً:\n{data}")
    except Exception as e:
        bot.reply_to(message, f"⚠️ خطأ: {e}")

# 🚀 دالة النشر
def send_random_clip():
    with db_lock:
        try:
            with open(DB_FILE, "r") as f:
                all_posts = json.load(f)
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
        except: return

    if not all_posts: return
    
    available = [p for p in all_posts if p not in history]
    if not available:
        history = []
        available = all_posts

    selected = random.choice(available)
    try:
        bot.copy_messages(chat_id=PUBLIC_CHANNEL, from_chat_id=PRIVATE_CHANNEL, message_ids=selected)
        history.append(selected)
        with db_lock:
            with open(HISTORY_FILE, "w") as f:
                json.dump(history, f)
    except Exception as e:
        print(f"❌ خطأ في النشر: {e}")

@app.route('/')
def home(): return "البوت يعمل بنجاح 🚀"

# ⏰ المجدول
scheduler = BackgroundScheduler(timezone="Asia/Riyadh")
scheduler.add_job(send_random_clip, 'interval', minutes=5)
scheduler.start()

if __name__ == "__main__":
    try: bot.remove_webhook()
    except: pass
    
    # تشغيل البوت مع تحديد نوع التحديثات المطلوبة
    threading.Thread(target=lambda: bot.infinity_polling(allowed_updates=['channel_post', 'message']), daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
