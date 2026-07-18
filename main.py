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

DB_FILE = "database.json"
db_lock = threading.Lock()  # قفل ذكي لمنع تجمد أو تداخل البيانات أثناء القراءة والكتابة

# إنشاء ملف الذاكرة إذا لم يكن موجوداً
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump([], f)

# مخزن مؤقت لتجميع الرسائل الحالية قبل حفظها
temp_post_ids = []

# 📡 المستشعر الذكي: يراقب قناة المخزن ويسجل المنشورات تلقائياً
@bot.channel_post_handler(func=lambda message: message.chat.id == PRIVATE_CHANNEL)
def auto_save_posts(message):
    global temp_post_ids
    
    # إذا كانت الرسالة نصية صافية (بدون ميديا) فهذا يعني أنها النص الشارح (نهاية المنشور)
    if message.text and not (message.photo or message.video or message.animation or message.document):
        if temp_post_ids:
            temp_post_ids.append(message.message_id)
            
            # حفظ المجموعة بأمان داخل ملف الذاكرة باستخدام القفل المشترك
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
                        
            print(f"💾 تم رصد وحفظ منشور جديد في الذاكرة: {temp_post_ids}")
            temp_post_ids = [] # تصفير المخزن للمنشور القادم
    else:
        # إذا كانت الرسالة ميديا (فيديو واحد أو مجموعة وسائط متتالية) نضيف رقمها للمجموعة
        temp_post_ids.append(message.message_id)

# 🚀 دالة النشر العشوائي الحقيقي
def send_random_clip():
    print("🔍 جاري اختيار منشور عشوائي من الذاكرة...")
    
    with db_lock:
        try:
            with open(DB_FILE, "r") as f:
                all_posts = json.load(f)
        except Exception as e:
            print(f"❌ خطأ في قراءة ملف الذاكرة: {e}")
            return

    if not all_posts:
        print("⚠️ الذاكرة فارغة! لا توجد منشورات مسجلة للنشر حالياً.")
        return
        
    # اختيار عشوائي حقيقي ومحدث في كل مرة تشتغل فيها الدالة
    selected_post = random.choice(all_posts)
    
    try:
        # نسخ الرسائل ككتلة واحدة وبنفس الترتيب وبدون كلمة "محول من"
        bot.copy_messages(
            chat_id=PUBLIC_CHANNEL,
            from_chat_id=PRIVATE_CHANNEL,
            message_ids=selected_post
        )
        print(f"✅ تم بنجاح نشر المنشور ذو المعرفات: {selected_post}")
    except Exception as e:
        print(f"❌ حدث خطأ أثناء النشر للمجموعة {selected_post}: {e}")

@app.route('/')
def home():
    return "بوت النشر التلقائي الذكي يعمل بنجاح وبأعلى درجات الاستقرار!"

# ⏰ ضبط توقيت الحملة (بتوقيت الرياض)
scheduler = BackgroundScheduler(timezone="Asia/Riyadh")

# النشر كل 5 دقائق ابتداءً من الساعة 7 مساءً (19) وحتى نهاية اليوم
scheduler.add_job(send_random_clip, 'cron', hour='19-23', minute='*/5')
scheduler.start()

if __name__ == "__main__":
    # تشغيل مستمع البوت في الخلفية لمراقبة القناة دون التأثير على سيرفر الويب
    threading.Thread(target=lambda: bot.infinity_polling(timeout=10, long_polling_timeout=5), daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    
    # 🛑 الإصلاح الأهم: إيقاف الـ reloader والـ debug لمنع تشغيل الكود مرتين وتجنب الحظر
    app.run(host="0.0.0.0", port=port, use_reloader=False, debug=False)
