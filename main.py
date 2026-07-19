import telebot
import random
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import os
import json
import threading

# 1. 🔑 توكن البوت
BOT_TOKEN = "8990766814:AAG9oGNq2ZO8DQCZZZCOPcB1sglntbdPQKo"
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

# 2. 📺 أرقام القنوات
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

# دالة حفظ المنشور
def save_post_to_db(post_ids):
    with db_lock:
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
        except:
            data = []
        
        # التأكد من عدم تكرار حفظ نفس المعرفات
        if post_ids not in data:
            data.append(post_ids)
            with open(DB_FILE, "w") as f:
                json.dump(data, f)
            print(f"💾 تم رصد وحفظ منشور جديد (IDs: {post_ids})")

# 📡 مستشعر القناة المطور
@bot.channel_post_handler(func=lambda message: message.chat.id == PRIVATE_CHANNEL)
def auto_save_posts(message):
    # إذا كانت الرسالة جزءاً من مجموعة (فيديو + نص مرسلين معاً)
    if message.media_group_id:
        # هنا البوت سيحفظ كل جزء من المجموعة كمنشور منفصل لضمان عدم ضياع أي جزء
        save_post_to_db([message.message_id])
    else:
        # إذا كانت رسالة عادية (فيديو فقط أو نص فقط)
        save_post_to_db([message.message_id])

# 🛠️ أمر فحص الذاكرة
@bot.message_handler(commands=['db'])
def check_db(message):
    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)
        bot.reply_to(message, f"📂 عدد المقاطع المحفوظة: {len(data)}\n{data}")
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
        # copy_messages تنقل الرسالة بكل محتوياتها
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
    
    # تشغيل البوت
    threading.Thread(target=lambda: bot.infinity_polling(allowed_updates=['channel_post', 'message']), daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
