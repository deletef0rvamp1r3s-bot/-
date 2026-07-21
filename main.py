import telebot
import random
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import os
import json
import threading
import io  # 🆕 مكتبة جديدة للتعامل مع الملفات وهمياً لتخطي حد الحروف

# 1. 🔑 توكن البوت الخاص بك
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8990766814:AAFom2ZDjJLvpN7w3x1pRUF2r3-qcHIhj9A")
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

# 🔄 1. جلب البيانات من الملف المثبت (أو النص القديم للتحويل التلقائي)
def get_cloud_db():
    try:
        chat = bot.get_chat(PRIVATE_CHANNEL)
        pinned_msg = chat.pinned_message
        
        if pinned_msg:
            # إذا كان النظام الجديد (ملف)
            if pinned_msg.document:
                file_info = bot.get_file(pinned_msg.document.file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                return json.loads(downloaded_file), pinned_msg.message_id
            
            # إذا كان النظام القديم (نص) لسحب البيانات بسلاسة أول مرة
            elif pinned_msg.text and '{"posts":' in pinned_msg.text:
                return json.loads(pinned_msg.text), pinned_msg.message_id
                
    except Exception as e:
        print(f"⚠️ تنبيه أثناء جلب الذاكرة السحابية: {e}")
        
    return {"posts": INITIAL_POSTS, "history": []}, None

# 🔄 2. حفظ البيانات على شكل ملف بدل النص لتفادي حد الـ 4096 حرف
def save_cloud_db(db_data, old_msg_id):
    try:
        # تحويل البيانات إلى نص ثم إلى ملف وهمي
        json_str = json.dumps(db_data, indent=2)
        file_stream = io.BytesIO(json_str.encode('utf-8'))
        file_stream.name = 'database.json'
        
        # إرسال الملف الجديد للقناة
        msg = bot.send_document(
            chat_id=PRIVATE_CHANNEL, 
            document=file_stream, 
            caption="📦 قاعدة البيانات السحابية (نظام الملفات)"
        )
        
        # تثبيت الملف الجديد بصمت
        bot.pin_chat_message(chat_id=PRIVATE_CHANNEL, message_id=msg.message_id, disable_notification=True)
        
        # حذف الرسالة القديمة (نصية أو ملف) لكي لا تمتلئ القناة
        if old_msg_id:
            try:
                bot.delete_message(chat_id=PRIVATE_CHANNEL, message_id=old_msg_id)
            except Exception as e:
                pass # تجاهل الخطأ إذا تعذر الحذف
                
    except Exception as e:
        print(f"❌ خطأ أثناء حفظ قاعدة البيانات: {e}")

# 📡 مستشعر ذكي وسحابي (يستقبل ويحفظ الجديد فوراً)
@bot.channel_post_handler(content_types=['text', 'photo', 'video', 'animation', 'document', 'audio', 'voice'])
def auto_save_posts(message):
    if message.chat.id != PRIVATE_CHANNEL:
        return
        
    # تجاهل ملف قاعدة البيانات نفسه
    if message.document and message.document.file_name == 'database.json':
        return
    # تجاهل رسالة قاعدة البيانات النصية القديمة
    if message.text and message.text.startswith('{"posts":'):
        return  

    with db_lock:
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

# 🛠️ أمر فحص الذاكرة
@bot.message_handler(commands=['db'])
def check_db(message):
    try:
        db_data, _ = get_cloud_db()
        simplified_data = [block["ids"] for block in db_data.get("posts", [])]
        bot.reply_to(message, f"📂 إجمالي المنشورات: {len(simplified_data)}\nالنظام المستخدم: نظام الملفات (بلا حدود) 🚀")
    except Exception as e:
        bot.reply_to(message, f"⚠️ خطأ: {e}")

# 🚀 دالة النشر العشوائي السحابي
def send_random_clip():
    with db_lock:
        db_data, msg_id = get_cloud_db()
        all_blocks = db_data.get("posts", [])
        history = db_data.get("history", [])

    if not all_blocks: 
        return
    
    available = [b for b in all_blocks if b["ids"] not in history]
    
    if not available:
        print("🔄 تم نشر جميع المقاطع، جاري إعادة تصفير السجل سحابياً للبدء من جديد...")
        history = []
        available = all_blocks

    selected_block = random.choice(available)
    selected_ids = selected_block["ids"]
    
    try:
        bot.copy_messages(chat_id=PUBLIC_CHANNEL, from_chat_id=PRIVATE_CHANNEL, message_ids=selected_ids)
        print(f"✅ تم النشر العشوائي بنجاح للكتلة: {selected_ids}")
        
        history.append(selected_ids)
        db_data["history"] = history
        
        with db_lock:
            save_cloud_db(db_data, msg_id)
    except Exception as e:
        print(f"❌ حدث خطأ أثناء النشر: {e}")

@app.route('/')
def home():
    return "قاعدة البيانات السحابية (نظام الملفات) تعمل بنجاح واستقرار أزلي 🚀"

# ⏰ المجدول الدقيق (من الساعة 12 الليل إلى 2 الليل كل 7 دقائق)
scheduler = BackgroundScheduler(timezone="Asia/Riyadh")
scheduler.add_job(send_random_clip, 'cron', hour=0, minute='*/7', misfire_grace_time=600, max_instances=3)
scheduler.add_job(send_random_clip, 'cron', hour=1, minute='*/7', misfire_grace_time=600, max_instances=3)
scheduler.add_job(send_random_clip, 'cron', hour=2, minute=0, misfire_grace_time=600, max_instances=3)
scheduler.start()

if __name__ == "__main__":
    try: 
        bot.remove_webhook()
    except Exception as e: 
        pass
    
    threading.Thread(target=lambda: bot.infinity_polling(allowed_updates=['channel_post', 'message'], skip_pending=True), daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False, debug=False)
