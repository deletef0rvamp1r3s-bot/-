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

# 2. 📺 أرقام القنوات
PRIVATE_CHANNEL = -1004495050725  # قناة المخزن السري
PUBLIC_CHANNEL = -1004102734458   # قناة الإعلانات العامة

# 3. 🗂️ ملفات الذاكرة والسجل
DB_FILE = "database.json"
HISTORY_FILE = "history.json" # ملف جديد لمنع تكرار المقاطع
db_lock = threading.Lock()

# إنشاء ملفات الذاكرة إذا لم تكن موجودة
for file in [DB_FILE, HISTORY_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump([], f)

temp_post_ids = []

# 🛠️ أمر خاص بالآدمن لفحص الذاكرة من تليجرام مباشرة
@bot.message_handler(commands=['db'])
def check_db(message):
    try:
        with open(DB_FILE, "r") as f:
            data = f.read()
        bot.reply_to(message, f"📂 محتوى الذاكرة حالياً:\n{data}")
    except Exception as e:
        bot.reply_to(message, f"⚠️ خطأ في قراءة الذاكرة: {e}")

# 📡 المستشعر الذكي: يراقب قناة المخزن ويسجل المنشورات
@bot.channel_post_handler(func=lambda message: message.chat.id == PRIVATE_CHANNEL)
def auto_save_posts(message):
    global temp_post_ids
    
    if message.text and not (message.photo or message.video or message.animation or message.document):
        if temp_post_ids:
            temp_post_ids.append(message.message_id)
            
            with db_lock:
                try:
                    with open(DB_FILE, "r") as f:
                        data = json.load(f)
                except:
                    data = []
                    
                if temp_post_ids not in data:
                    data.append(temp_post_ids)
                    with open(DB_FILE, "w") as f:
                        json.dump(data, f)
                        
            print(f"💾 تم رصد وحفظ منشور جديد: {temp_post_ids}")
            temp_post_ids = []
    else:
        temp_post_ids.append(message.message_id)

# 🚀 دالة النشر العشوائي (بدون تكرار)
def send_random_clip():
    print("🔍 جاري اختيار منشور عشوائي...")
    
    with db_lock:
        try:
            with open(DB_FILE, "r") as f:
                all_posts = json.load(f)
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
        except Exception as e:
            print(f"❌ خطأ في قراءة الملفات: {e}")
            return

    if not all_posts:
        print("⚠️ الذاكرة فارغة! بانتظار إضافة منشورات في المخزن.")
        return
        
    # استبعاد المقاطع التي تم نشرها مؤخراً لمنع التكرار
    available_posts = [p for p in all_posts if p not in history]
    
    # إذا تم نشر كل المقاطع، نصفر السجل لنبدأ دورة جديدة
    if not available_posts:
        print("🔄 تم نشر جميع المقاطع مسبقاً، جاري تصفير السجل للبدء من جديد...")
        history = []
        available_posts = all_posts

    # اختيار عشوائي من المقاطع المتاحة (من فوق، وسط، أو تحت)
    selected_post = random.choice(available_posts)
    
    try:
        # النقل ككتلة واحدة وبدون حقوق
        bot.copy_messages(
            chat_id=PUBLIC_CHANNEL,
            from_chat_id=PRIVATE_CHANNEL,
            message_ids=selected_post
        )
        print(f"✅ تم النشر بنجاح: {selected_post}")
        
        # تسجيل المقطع في سجل المنشورات لمنع تكراره
        history.append(selected_post)
        with db_lock:
            with open(HISTORY_FILE, "w") as f:
                json.dump(history, f)
                
    except Exception as e:
        print(f"❌ حدث خطأ أثناء النشر: {e}")

@app.route('/')
def home():
    return "البوت يعمل بنجاح ومستقر 100% 🚀"

# ⏰ ضبط التوقيت: النشر كل 15 دقيقة (تستطيع تغيير الرقم 15 لأي رقم تريده)
scheduler = BackgroundScheduler(timezone="Asia/Riyadh")
scheduler.add_job(send_random_clip, 'interval', minutes=5)
scheduler.start()

if __name__ == "__main__":
    # 🛑 مسح أي تعارض سابق يمنع البوت من استلام الرسائل
    try:
        bot.remove_webhook()
    except:
        pass
        
    # تشغيل البوت في الخلفية مع حماية ضد التوقف
    threading.Thread(target=lambda: bot.infinity_polling(timeout=10, long_polling_timeout=5), daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False, debug=False)
