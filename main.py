import telebot
from telebot import apihelper # 👈 ضرورية لمنع التعليق
import random
import time
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import os
import json
import threading
import io
import pytz # 👈 تمت إضافة مكتبة التوقيت
from datetime import datetime # 👈 تمت إضافتها لفحص الوقت

# 1. 🔑 توكن البوت
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("⚠️ تحذير: يرجى إضافة BOT_TOKEN في متغيرات البيئة على المنصة!")

# 👇 حماية البوت من تعليق سيرفرات تليجرام (يفصل المحاولة لو تأخرت أكثر من 20 ثانية)
apihelper.READ_TIMEOUT = 20
apihelper.CONNECT_TIMEOUT = 20

bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

# 2. 📺 أرقام القنوات
PRIVATE_CHANNEL = -1004495050725
PUBLIC_CHANNEL = -1004102734458

# 📦 الـ 43 مقطع الأساسية الخاصة بك
INITIAL_POSTS = [
    {"ids": [499, 500], "media_group_id": None}, {"ids": [501, 502], "media_group_id": None},
    {"ids": [503, 504], "media_group_id": None}, {"ids": [505, 506], "media_group_id": None},
    {"ids": [507, 508, 509], "media_group_id": None}, {"ids": [510, 511], "media_group_id": None},
    {"ids": [512, 513], "media_group_id": None}, {"ids": [514, 516, 515], "media_group_id": None},
    {"ids": [517, 518], "media_group_id": None}, {"ids": [519, 520], "media_group_id": None},
    {"ids": [521, 522, 523], "media_group_id": None}, {"ids": [524, 525], "media_group_id": None},
    {"ids": [526, 527], "media_group_id": None}, {"ids": [528, 530, 529, 531], "media_group_id": None},
    {"ids": [532, 533], "media_group_id": None}, {"ids": [534, 535], "media_group_id": None},
    {"ids": [536, 537], "media_group_id": None}, {"ids": [538, 539, 540, 541], "media_group_id": None},
    {"ids": [542, 543], "media_group_id": None}, {"ids": [544, 545], "media_group_id": None},
    {"ids": [546, 547], "media_group_id": None}, {"ids": [548, 549], "media_group_id": None},
    {"ids": [550, 551], "media_group_id": None}, {"ids": [552, 554, 553, 555], "media_group_id": None},
    {"ids": [556, 557], "media_group_id": None}, {"ids": [558, 560, 559, 561, 562], "media_group_id": None},
    {"ids": [563, 564], "media_group_id": None}, {"ids": [565, 567, 566, 568], "media_group_id": None},
    {"ids": [569, 570, 572, 571, 574, 573, 575], "media_group_id": None}, {"ids": [576, 577], "media_group_id": None},
    {"ids": [578, 579], "media_group_id": None}, {"ids": [580, 581, 582, 583], "media_group_id": None},
    {"ids": [584, 585, 586], "media_group_id": None}, {"ids": [587, 588], "media_group_id": None},
    {"ids": [589, 590], "media_group_id": None}, {"ids": [591, 592, 593, 594], "media_group_id": None},
    {"ids": [595, 596], "media_group_id": None}, {"ids": [597, 598], "media_group_id": None},
    {"ids": [599, 600, 601], "media_group_id": None}, {"ids": [602, 603], "media_group_id": None},
    {"ids": [604, 605], "media_group_id": None}, {"ids": [606, 608, 607, 609], "media_group_id": None},
    {"ids": [610, 611, 1840, 1841, 1842], "media_group_id": None}
]

db_lock = threading.Lock()

# 🔄 1. جلب البيانات من الرسالة المثبتة
def get_cloud_db():
    try:
        chat = bot.get_chat(PRIVATE_CHANNEL)
        pinned_msg = chat.pinned_message
        
        if pinned_msg:
            if pinned_msg.document:
                file_info = bot.get_file(pinned_msg.document.file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                return json.loads(downloaded_file), pinned_msg.message_id
            elif pinned_msg.text and '{"posts":' in pinned_msg.text:
                return json.loads(pinned_msg.text), pinned_msg.message_id
    except Exception as e:
        print(f"⚠️ تنبيه أثناء جلب الذاكرة: {e}")
        
    return {"posts": INITIAL_POSTS, "history": []}, None

# 🔄 2. حفظ البيانات وتثبيتها في القناة
def save_cloud_db(db_data, old_msg_id):
    try:
        json_str = json.dumps(db_data, indent=2)
        file_stream = io.BytesIO(json_str.encode('utf-8'))
        file_stream.name = 'database.json'
        
        # إرسال الملف للقناة
        msg = bot.send_document(
            chat_id=PRIVATE_CHANNEL, 
            document=file_stream, 
            caption="📦 قاعدة البيانات السحابية (نظام الملفات)"
        )
        
        # 📌 تثبيت رسالة الداتا بيس بصمت
        bot.pin_chat_message(chat_id=PRIVATE_CHANNEL, message_id=msg.message_id, disable_notification=True)
        
        # حذف الملف القديم لعدم الإزعاج
        if old_msg_id:
            try:
                bot.delete_message(chat_id=PRIVATE_CHANNEL, message_id=old_msg_id)
            except Exception:
                pass
    except Exception as e:
        print(f"❌ خطأ أثناء حفظ قاعدة البيانات: {e}")

# 📡 مستشعر الحفظ التلقائي (محمي من التعليق)
@bot.channel_post_handler(content_types=['text', 'photo', 'video', 'animation', 'document', 'audio', 'voice'])
def auto_save_posts(message):
    if message.chat.id != PRIVATE_CHANNEL:
        return
        
    if message.document and message.document.file_name == 'database.json':
        return
    if message.text and message.text.startswith('{"posts":'):
        return  

    if not db_lock.acquire(timeout=15):
        print("⚠️ تعذر حفظ المقطع التلقائي الآن لتجنب التعليق.")
        return
        
    try:
        db_data, msg_id = get_cloud_db()
        data = db_data.get("posts", [])

        if message.media_group_id:
            found = False
            for block in reversed(data):
                if block.get("media_group_id") == str(message.media_group_id):
                    if message.message_id not in block["ids"]:
                        block["ids"].append(message.message_id)
                    found = True
                    break
            if not found:
                data.append({"ids": [message.message_id], "media_group_id": str(message.media_group_id)})
        elif message.content_type == 'text':
            if data:
                if message.message_id not in data[-1]["ids"]:
                    data[-1]["ids"].append(message.message_id)
            else:
                data.append({"ids": [message.message_id], "media_group_id": None})
        else:
            data.append({"ids": [message.message_id], "media_group_id": None})

        db_data["posts"] = data
        save_cloud_db(db_data, msg_id)
    finally:
        db_lock.release()

# 🛠️ أمر فحص الذاكرة
@bot.message_handler(commands=['db'])
def check_db(message):
    try:
        db_data, _ = get_cloud_db()
        simplified_data = [block["ids"] for block in db_data.get("posts", [])]
        bot.reply_to(message, f"📂 إجمالي المنشورات: {len(simplified_data)}\nالنظام المستخدم: نظام الملفات (بلا حدود) 🚀")
    except Exception as e:
        bot.reply_to(message, f"⚠️ خطأ: {e}")

# 🛠️ أمر فحص الوقت (للتأكد أن البوت يقرأ توقيت السعودية صح)
@bot.message_handler(commands=['time'])
def check_time(message):
    try:
        saudi_tz = pytz.timezone("Asia/Riyadh")
        saudi_time = datetime.now(saudi_tz).strftime("%Y-%m-%d %H:%M:%S")
        bot.reply_to(message, f"🕒 الوقت الحالي في عقل البوت (توقيت السعودية) هو:\n{saudi_time}")
    except Exception as e:
        bot.reply_to(message, f"⚠️ خطأ أثناء قراءة الوقت: {e}")

# 🛠️ أمر لاختبار النشر يدوياً (للتأكد أن الصلاحيات سليمة)
@bot.message_handler(commands=['test'])
def manual_test_post(message):
    bot.reply_to(message, "⏳ جاري محاولة نشر مقطع عشوائي الآن لاختبار الكود...")
    threading.Thread(target=send_random_clip).start()

# 🚀 دالة النشر العشوائي السحابي (محمية وعشوائية 100%)
def send_random_clip():
    if not db_lock.acquire(timeout=15):
        print("⚠️ القفل مشغول، سيتم تخطي هذه الدورة لتجنب تعليق البوت.")
        return
        
    try:
        db_data, msg_id = get_cloud_db()
        all_blocks = db_data.get("posts", [])
        history = db_data.get("history", [])
    finally:
        db_lock.release() 

    if not all_blocks: 
        return
    
    max_retries = 5  
    
    for attempt in range(max_retries):
        # فلترة المقاطع التي لم تُنشر بعد
        available = [b for b in all_blocks if b["ids"] not in history]
        
        if not available:
            print("🔄 تم نشر جميع المقاطع، جاري إعادة تصفير السجل سحابياً...")
            history = []
            available = all_blocks

        # 🎲 هنا يتم الاختيار العشوائي التام (لا يهم إن كان المقطع بأول القناة أو آخرها)
        selected_block = random.choice(available)
        selected_ids = selected_block["ids"]
        
        try:
            bot.copy_messages(chat_id=PUBLIC_CHANNEL, from_chat_id=PRIVATE_CHANNEL, message_ids=selected_ids)
            print(f"✅ تم النشر العشوائي بنجاح للكتلة: {selected_ids}")
            
            history.append(selected_ids)
            db_data["history"] = history
            
            if db_lock.acquire(timeout=15):
                try:
                    save_cloud_db(db_data, msg_id)
                finally:
                    db_lock.release()
            break  
            
        except Exception as e:
            print(f"❌ حدث خطأ أثناء النشر (محاولة {attempt+1}): {e}")
            error_text = str(e).lower()
            if "not found" in error_text or "message to copy" in error_text:
                history.append(selected_ids)
                db_data["history"] = history
                if db_lock.acquire(timeout=15):
                    try:
                        save_cloud_db(db_data, msg_id)
                    finally:
                        db_lock.release()
            
            time.sleep(3) 
    else:
        print("⚠️ فشلت جميع المحاولات لنشر مقطع في هذا الوقت.")

@app.route('/')
def home():
    return "قاعدة البيانات السحابية تعمل بنجاح 🚀"

# ⏰ المجدول (كما هو تماماً ليتوقف بعد الساعة 2 صباحاً)
scheduler = BackgroundScheduler(timezone="Asia/Riyadh")
scheduler.add_job(send_random_clip, 'cron', hour=0, minute='*/7', misfire_grace_time=600, max_instances=3)
scheduler.add_job(send_random_clip, 'cron', hour=1, minute='*/7', misfire_grace_time=600, max_instances=3)
scheduler.add_job(send_random_clip, 'cron', hour=2, minute=0, misfire_grace_time=600, max_instances=3)
scheduler.start()

if __name__ == "__main__":
    try: 
        bot.remove_webhook()
    except Exception: 
        pass
    
    threading.Thread(target=lambda: bot.infinity_polling(allowed_updates=['channel_post', 'message'], skip_pending=True), daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False, debug=False)
