import telebot
from telebot import apihelper
import random
import time
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import os
import json
import threading
import io
import pytz
from datetime import datetime

# 1. 🔑 توكن البوت
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("⚠️ تحذير: يرجى إضافة BOT_TOKEN في متغيرات البيئة على المنصة!")

# 👇 حماية البوت من تعليق سيرفرات تليجرام
apihelper.READ_TIMEOUT = 20
apihelper.CONNECT_TIMEOUT = 20

bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

# 2. 📺 أرقام القنوات
PRIVATE_CHANNEL = -1004495050725
PUBLIC_CHANNEL = -1004102734458

db_lock = threading.Lock()

# 🔄 1. جلب البيانات من القناة فقط (بدون أي تخزين داخل الكود)
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
        print(f"⚠️ تنبيه أثناء جلب الذاكرة (قد لا يوجد ملف مثبت بعد): {e}")
        
    # إذا لم يجد ملف في القناة، يبدأ بقاعدة بيانات فارغة جديدة
    return {"posts": [], "history": []}, None

# 🔄 2. حفظ البيانات وتثبيتها في القناة
def save_cloud_db(db_data, old_msg_id):
    try:
        json_str = json.dumps(db_data, indent=2)
        file_stream = io.BytesIO(json_str.encode('utf-8'))
        file_stream.name = 'database.json'
        
        msg = bot.send_document(
            chat_id=PRIVATE_CHANNEL, 
            document=file_stream, 
            caption="📦 قاعدة البيانات السحابية (نظام الملفات)"
        )
        
        bot.pin_chat_message(chat_id=PRIVATE_CHANNEL, message_id=msg.message_id, disable_notification=True)
        
        if old_msg_id:
            try:
                bot.delete_message(chat_id=PRIVATE_CHANNEL, message_id=old_msg_id)
            except Exception:
                pass
    except Exception as e:
        print(f"❌ خطأ أثناء حفظ قاعدة البيانات: {e}")

# 📡 مستشعر الحفظ التلقائي
@bot.channel_post_handler(content_types=['text', 'photo', 'video', 'animation', 'document', 'audio', 'voice'])
def auto_save_posts(message):
    if message.chat.id != PRIVATE_CHANNEL:
        return
        
    if message.document and message.document.file_name == 'database.json':
        return
    if message.text and message.text.startswith('{"posts":'):
        return  

    if not db_lock.acquire(timeout=15):
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
        bot.reply_to(message, f"📂 إجمالي المنشورات: {len(simplified_data)}\nالنظام المستخدم: الاعتماد الكلي على رسالة القناة 🚀")
    except Exception as e:
        bot.reply_to(message, f"⚠️ خطأ: {e}")

# 🛠️ أمر فحص الوقت
@bot.message_handler(commands=['time'])
def check_time(message):
    try:
        saudi_tz = pytz.timezone("Asia/Riyadh")
        saudi_time = datetime.now(saudi_tz).strftime("%Y-%m-%d %H:%M:%S")
        bot.reply_to(message, f"🕒 الوقت الحالي في عقل البوت (توقيت السعودية) هو:\n{saudi_time}")
    except Exception as e:
        bot.reply_to(message, f"⚠️ خطأ أثناء قراءة الوقت: {e}")

# 🛠️ أمر اختبار النشر 
@bot.message_handler(commands=['test'])
def manual_test_post(message):
    bot.reply_to(message, "⏳ جاري محاولة النشر...")
    try:
        db_data, _ = get_cloud_db()
        all_blocks = db_data.get("posts", [])
        if not all_blocks:
            bot.reply_to(message, "⚠️ قاعدة البيانات فارغة! قم بإرسال مقاطع للقناة الخاصة أولاً.")
            return
            
        selected_block = random.choice(all_blocks)
        selected_ids = sorted(selected_block["ids"]) 
        
        bot.copy_messages(chat_id=PUBLIC_CHANNEL, from_chat_id=PRIVATE_CHANNEL, message_ids=selected_ids)
        bot.reply_to(message, f"✅ تم النشر بنجاح للكتلة: {selected_ids}")
    except Exception as e:
        bot.reply_to(message, f"❌ تليجرام يرفض النشر!\nالسبب: {e}")

# 🚀 دالة النشر العشوائي للمجدول
def send_random_clip():
    if not db_lock.acquire(timeout=15):
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
        available = [b for b in all_blocks if b["ids"] not in history]
        
        if not available:
            print("🔄 تم نشر جميع المقاطع، جاري إعادة تصفير السجل سحابياً...")
            history = []
            available = all_blocks

        selected_block = random.choice(available)
        selected_ids = sorted(selected_block["ids"])
        
        try:
            bot.copy_messages(chat_id=PUBLIC_CHANNEL, from_chat_id=PRIVATE_CHANNEL, message_ids=selected_ids)
            print(f"✅ تم النشر العشوائي بنجاح للكتلة: {selected_ids}")
            
            history.append(selected_block["ids"]) 
            db_data["history"] = history
            
            if db_lock.acquire(timeout=15):
                try:
                    save_cloud_db(db_data, msg_id)
                finally:
                    db_lock.release()
            break  
            
        except Exception as e:
            print(f"❌ حدث خطأ أثناء النشر: {e}")
            error_text = str(e).lower()
            if "not found" in error_text or "message to copy" in error_text:
                history.append(selected_block["ids"])
                db_data["history"] = history
                if db_lock.acquire(timeout=15):
                    try:
                        save_cloud_db(db_data, msg_id)
                    finally:
                        db_lock.release()
            
            time.sleep(3) 

@app.route('/')
def home():
    return "قاعدة البيانات السحابية تعمل بنجاح 🚀"

# ⏰ المجدول (نشر كل 7 دقائق من 12 إلى 2 صباحاً)
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
    
    # 👇 هنا التعديل تم بنجاح: skip_pending=False
    threading.Thread(target=lambda: bot.infinity_polling(allowed_updates=['channel_post', 'message'], skip_pending=False), daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False, debug=False)
