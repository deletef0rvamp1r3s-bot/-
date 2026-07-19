import telebot
import random
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import os
import json
import threading

# 1. 🔑 توكن البوت الخاص بك
BOT_TOKEN = "8990766814:AAEcM-Esq3LMRpBLcpNrAkYxSGfEowVhujI"
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

# 2. 📺 أرقام القنوات
PRIVATE_CHANNEL = -1004495050725
PUBLIC_CHANNEL = -1004102734458

# 3. 🗂️ ملفات الذاكرة والسجل
DB_FILE = "database.json"
HISTORY_FILE = "history.json"
db_lock = threading.Lock()

# متغير لتتبع قروب الميديا (الصور/المقاطع المتعددة)
last_media_group_id = None

# إنشاء الملفات إذا لم تكن موجودة
for file in [DB_FILE, HISTORY_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump([], f)

# 📡 المستشعر الذكي جداً (يتعرف على المقاطع، قروب الميديا، والنص المفصول)
@bot.channel_post_handler(content_types=['text', 'photo', 'video', 'animation', 'document', 'audio', 'voice'])
def auto_save_posts(message):
    global last_media_group_id
    
    with db_lock:
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
        except:
            data = []

        # 1- إذا كانت الرسالة عبارة عن ميديا من ضمن "قروب ميديا"
        if message.media_group_id:
            if message.media_group_id == last_media_group_id and data:
                # إضافة المعرف للقروب الحالي لتصبح كتلة واحدة
                if message.message_id not in data[-1]:
                    data[-1].append(message.message_id)
                    print(f"🔗 تم دمج ملف إضافي لقروب الميديا: {message.message_id}")
            else:
                # قروب ميديا جديد
                data.append([message.message_id])
                last_media_group_id = message.media_group_id
                print(f"💾 تم رصد قروب ميديا جديد: {message.message_id}")
                
        # 2- إذا كانت الرسالة نصية فقط (الشرح المنفصل الذي تحت المقطع)
        elif message.content_type == 'text':
            if data and message.message_id not in data[-1]:
                data[-1].append(message.message_id)
                print(f"📄 تم ربط النص {message.message_id} بالمقطع/القروب السابق.")
            # تصفير القروب لأن النص يغلق الكتلة
            last_media_group_id = None
            
        # 3- إذا كانت الرسالة ميديا فردية (مقطع واحد أو صورة واحدة بدون قروب)
        else:
            data.append([message.message_id])
            last_media_group_id = None
            print(f"💾 تم رصد مقطع/ملف فردي جديد: {message.message_id}")

        # حفظ التعديلات في قاعدة البيانات
        with open(DB_FILE, "w") as f:
            json.dump(data, f)

# 🛠️ أمر خاص لفحص الذاكرة
@bot.message_handler(commands=['db'])
def check_db(message):
    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)
        bot.reply_to(message, f"📂 إجمالي المنشورات المحفوظة: {len(data)}\nمحتوى الذاكرة:\n{data}")
    except Exception as e:
        bot.reply_to(message, f"⚠️ خطأ: {e}")

# 🚀 دالة النشر العشوائي (بدون تكرار)
def send_random_clip():
    with db_lock:
        try:
            with open(DB_FILE, "r") as f:
                all_posts = json.load(f)
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
        except: 
            return

    if not all_posts: 
        return
    
    # فلترة المنشورات التي لم تنشر بعد
    available = [p for p in all_posts if p not in history]
    
    if not available:
        print("🔄 تم نشر جميع المقاطع، جاري تصفير السجل للبدء من جديد...")
        history = []
        available = all_posts

    # اختيار عشوائي (من أول أو وسط أو آخر القناة)
    selected = random.choice(available)
    
    try:
        # copy_messages تأخذ قائمة من المعرفات (سواء مقطع واحد أو مقطع + نص أو قروب ميديا + نص)
        # وتقوم بنشرها ككتلة واحدة بنفس الترتيب
        bot.copy_messages(
            chat_id=PUBLIC_CHANNEL, 
            from_chat_id=PRIVATE_CHANNEL, 
            message_ids=selected
        )
        print(f"✅ تم النشر العشوائي بنجاح للكتلة: {selected}")
        
        # تسجيل الكتلة في سجل المنشورات
        history.append(selected)
        with db_lock:
            with open(HISTORY_FILE, "w") as f:
                json.dump(history, f)
                
    except Exception as e:
        print(f"❌ حدث خطأ أثناء النشر: {e}")

@app.route('/')
def home():
    return "البوت يعمل بكفاءة تامة 🚀"

# ⏰ المجدول
scheduler = BackgroundScheduler(timezone="Asia/Riyadh")
scheduler.add_job(send_random_clip, 'interval', minutes=5)
scheduler.start()

if __name__ == "__main__":
    try: 
        bot.remove_webhook()
    except: 
        pass
    
    # تشغيل البوت في الخلفية مع السماح بجميع التحديثات
    threading.Thread(target=lambda: bot.infinity_polling(allowed_updates=['channel_post', 'message']), daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False, debug=False)
