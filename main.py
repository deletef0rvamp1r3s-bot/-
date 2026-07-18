import telebot
import random
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import os
import json
import threading

# 1. 🔑 توكن البوت الخاص بك
BOT_TOKEN = "8990766814:AAHj-H3Ug3fbTVtqiGvrwgI49dOiW-eZOkA"
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

# 2. 📺 أرقام القنوات
PRIVATE_CHANNEL = -1004495050725  # قناة المخزن السري
PUBLIC_CHANNEL = -1004102734458   # قناة الإعلانات العامة
DB_FILE = "posts.json"

# 📦 3. قائمة المنشورات القديمة (اكتب منشوراتك القديمة هنا لضمان استقرارها)
# [رقم أول رسالة ميديا , رقم الرسالة النصية التي تحتها]
HARDCODED_POSTS = [
    [2, 3],    # المنشور الأول
    [4, 5],    # المنشور الثاني 
    # يمكنك إضافة بقية منشوراتك القديمة هنا بنفس النمط
]

# دالة ذكية لدمج المنشورات الثابتة مع المنشورات الجديدة المتكشفة تلقائياً
def load_all_posts():
    posts = list(HARDCODED_POSTS)
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                dynamic_posts = json.load(f)
                for p in dynamic_posts:
                    if p not in posts:
                        posts.append(p)
        except Exception as e:
            print(f"❌ خطأ في قراءة ملف الكاش المحفوظ: {e}")
    return posts

# دالة لحفظ المنشورات الجديدة التي يكتشفها البوت تلقائياً
def save_dynamic_post(start_id, end_id):
    dynamic_posts = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                dynamic_posts = json.load(f)
        except:
            dynamic_posts = []
            
    new_post = [start_id, end_id]
    if new_post not in dynamic_posts and new_post not in HARDCODED_POSTS:
        dynamic_posts.append(new_post)
        with open(DB_FILE, "w") as f:
            json.dump(dynamic_posts, f)
        print(f"💾 ذكاء اصطناعي: تم رصد وحفظ منشور جديد تلقائيًا: {new_post}")

# مخزن مؤقت لتتبع بداية ونهاية المنشور الحالي أثناء رفعه في المخزن
current_post = {"start_id": None, "last_id": None}

# 📡 المستشعر الذكي: يراقب قناة المخزن ويسجل المنشورات (ميديا + نص) تلقائياً فور نزولها
@bot.channel_post_handler(func=lambda message: message.chat.id == PRIVATE_CHANNEL)
def auto_indexer(message):
    global current_post
    
    # إذا كانت الرسالة نصية صافية (بدون ميديا، ألبوم، أو متحركات) فهذا يعني أنها الشرح (نهاية المنشور)
    if message.text and not message.media_group_id and not message.photo and not message.video and not message.animation:
        if current_post["start_id"] is not None:
            # نغلق المنشور هنا لأن النص هو آخر شيء ينزل تحت المقطع أو الألبوم
            save_dynamic_post(current_post["start_id"], message.message_id)
            # تصفير المخزن المؤقت للاستعداد للمنشور القادم
            current_post = {"start_id": None, "last_id": None}
    else:
        # إذا كانت الرسالة عبارة عن ميديا (فيديو، صورة، متحركة، أو ألبوم وسائط)
        if current_post["start_id"] is None:
            current_post["start_id"] = message.message_id
        current_post["last_id"] = message.message_id

# دالة النشر العشوائي الذكي
def send_random_clip():
    print("🔍 جاري اختيار منشور عشوائي للنشر...")
    all_posts = load_all_posts()
    
    if not all_posts:
        print("⚠️ لا توجد أي منشورات مسجلة حالياً للنشر!")
        return
        
    # اختيار عشوائي حقيقي ومحدث في كل ثانية تشتغل فيها الدالة
    selected_post = random.choice(all_posts)
    start_id = selected_post[0]
    end_id = selected_post[1]
    
    msg_ids = list(range(start_id, end_id + 1))
    
    try:
        # نسخ الرسائل ككتلة واحدة (سواء مقطع واحد + نص أو قروب ميديا + نص)
        bot.copy_messages(
            chat_id=PUBLIC_CHANNEL,
            from_chat_id=PRIVATE_CHANNEL,
            message_ids=msg_ids
        )
        print(f"✅ تم بنجاح اختيار ونشر المنشور ذو المعرفات: {msg_ids}")
    except Exception as e:
        print(f"❌ حدث خطأ أثناء النشر للرسائل {msg_ids}: {e}")

@app.route('/')
def home():
    return "بوت النشر التلقائي الذكي يعمل بنجاح وبأعلى درجات الاستقرار!"

# ⏰ 4. ضبط توقيت الحملة (بتوقيت الرياض)
scheduler = BackgroundScheduler(timezone="Asia/Riyadh")

# الفترة الأولى: من 12:00 منتصف الليل وحتى 12:50 الليل
scheduler.add_job(send_random_clip, 'cron', hour=18, minute='0,10,20,30,40,50')

# الفترة الثانية: من 1:00 بعد منتصف الليل وحتى 1:30 الليل
scheduler.add_job(send_random_clip, 'cron', hour=19, minute='0,10,20,30')

scheduler.start()

if __name__ == "__main__":
    # تشغيل مستمع البوت في الخلفية لاستقبال وتكشيف المنشورات الجديدة دون التأثير على Flask
    threading.Thread(target=lambda: bot.infinity_polling(allowed_updates=['channel_post']), daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
