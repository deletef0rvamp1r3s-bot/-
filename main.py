import telebot
import random
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import os
import json
import threading

# 1. 🔑 توكن البوت الخاص بك
BOT_TOKEN = "8990766814:AAFqaYY5NUaRW77fqZpyTVnY5SeIC9-_R00"
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

# 2. 📺 أرقام القنوات
PRIVATE_CHANNEL = -1004495050725
PUBLIC_CHANNEL = -1004102734458

# 3. 🗂️ ملفات الذاكرة والسجل
DB_FILE = "database.json"
HISTORY_FILE = "history.json"
db_lock = threading.Lock()

# إنشاء الملفات إذا لم تكن موجودة
for file in [DB_FILE, HISTORY_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump([], f)

# 📡 المستشعر الذكي والمعاد هندسته بالكامل (مقاوم للأخطاء)
@bot.channel_post_handler(content_types=['text', 'photo', 'video', 'animation', 'document', 'audio', 'voice'])
def auto_save_posts(message):
    with db_lock:
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
        except:
            data = []

        # 1- إذا كانت الرسالة جزءاً من قروب ميديا (ألبوم مقاطع أو صور)
        if message.media_group_id:
            found = False
            # البحث في الذاكرة عن قروب ميديا موجود مسبقاً يحمل نفس المعرف لدمجه معه
            for block in reversed(data):
                if block.get("media_group_id") == str(message.media_group_id):
                    if message.message_id not in block["ids"]:
                        block["ids"].append(message.message_id)
                    found = True
                    print(f"🔗 تم دمج ملف إضافي إلى قروب الميديا الحالي: {message.message_id}")
                    break
            
            # إذا كان أول ملف يصل من قروب الميديا، ننشئ له كتلة جديدة
            if not found:
                new_block = {
                    "ids": [message.message_id],
                    "media_group_id": str(message.media_group_id)
                }
                data.append(new_block)
                print(f"💾 تم إنشاء كتلة قروب ميديا جديدة: {message.message_id}")

        # 2- إذا كانت الرسالة نصية (الشرح المنفصل الذي يرسل تحت المقطع أو القروب)
        elif message.content_type == 'text':
            if data:
                # إلحاق النص بآخر كتلة ميديا تم تسجيلها فوراً لربطها بها
                if message.message_id not in data[-1]["ids"]:
                    data[-1]["ids"].append(message.message_id)
                    print(f"📄 تم ربط النص {message.message_id} بالمنشور السابق بنجاح.")
            else:
                # حالة احتياطية إذا أُرسل نص بدون أي ميديا سابقة
                data.append({"ids": [message.message_id], "media_group_id": None})
                print(f"📄 تم حفظ نص منفرد: {message.message_id}")
                
        # 3- إذا كانت ميديا فردية (مقطع واحد فقط أو صورة واحدة بدون قروب ميديا)
        else:
            new_block = {
                "ids": [message.message_id],
                "media_group_id": None
            }
            data.append(new_block)
            print(f"💾 تم رصد مقطع فردي جديد: {message.message_id}")

        # حفظ التعديلات الهيكلية في ملف الذاكرة
        with open(DB_FILE, "w") as f:
            json.dump(data, f)

# 🛠️ أمر فحص الذاكرة (تم تعديله ليعرض لك الأقواس مبسطة ومدمجة تماماً كما تحب)
@bot.message_handler(commands=['db'])
def check_db(message):
    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)
        # استخراج القوائم فقط لتبسيط العرض لك
        simplified_data = [block["ids"] for block in data]
        bot.reply_to(message, f"📂 إجمالي المنشورات المحفوظة: {len(simplified_data)}\nمحتوى الذاكرة الحالية:\n{simplified_data}")
    except Exception as e:
        bot.reply_to(message, f"⚠️ خطأ أثناء قراءة الذاكرة: {e}")

# 🚀 دالة النشر العشوائي الذكي (من أول أو وسط أو آخر القناة بدون تكرار)
def send_random_clip():
    with db_lock:
        try:
            with open(DB_FILE, "r") as f:
                all_blocks = json.load(f)
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
        except: 
            return

    if not all_blocks: 
        return
    
    # تصفية المنشورات (البلوكات) التي لم يتم نشرها بعد
    available = [b for b in all_blocks if b["ids"] not in history]
    
    # إذا انتهت كل المنشورات، صفر السجل وابدأ العشوائية من جديد
    if not available:
        print("🔄 تم نشر جميع المقاطع، جاري إعادة تصفير السجل للبدء من جديد...")
        history = []
        available = all_blocks

    # اختيار عشوائي تماماً (random.choice تضمن أخذ المنشور من أي مكان بالقناة)
    selected_block = random.choice(available)
    selected_ids = selected_block["ids"]
    
    try:
        # دالة copy_messages تنسخ الكتلة كاملة (المقاطع + النص التابع لها) دفعة واحدة وبترتيبها الصحيح
        bot.copy_messages(
            chat_id=PUBLIC_CHANNEL, 
            from_chat_id=PRIVATE_CHANNEL, 
            message_ids=selected_ids
        )
        print(f"✅ تم النشر العشوائي بنجاح للكتلة: {selected_ids}")
        
        # إضافة الكتلة المنشورة للسجل
        history.append(selected_ids)
        with db_lock:
            with open(HISTORY_FILE, "w") as f:
                json.dump(history, f)
                
    except Exception as e:
        print(f"❌ حدث خطأ أثناء النشر: {e}")

@app.route('/')
def home():
    return "البوت يعمل بأعلى كفاءة واستقرار 🚀"

# ⏰ المجدول الدشين (كل 5 دقائق)
scheduler = BackgroundScheduler(timezone="Asia/Riyadh")
scheduler.add_job(send_random_clip, 'interval', minutes=5)
scheduler.start()

if __name__ == "__main__":
    try: 
        bot.remove_webhook()
    except: 
        pass
    
    # تشغيل مستشعر البوت في خلفية النظامอย่าง آمن
    threading.Thread(target=lambda: bot.infinity_polling(allowed_updates=['channel_post', 'message']), daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False, debug=False)
