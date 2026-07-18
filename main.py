import telebot
import random
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

# 1. 🔑 ضع توكن البوت الجديد اللي سويته في بوت فاذر هنا
BOT_TOKEN = "8990766814:AAHj-H3Ug3fbTVtqiGvrwgI49dOiW-eZOkA"
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

@app.route('/')
def home():
    return "بوت النشر التلقائي الذكي يعمل ويكتشف المقاطع تلقائياً!"

# 2. 📺 أرقام القنوات الخاصة بك
PRIVATE_CHANNEL = -1004495050725  # قناة المخزن السري
PUBLIC_CHANNEL = -1004102734458   # قناة الإعلانات العامة

def get_dynamic_posts():
    """دالة ذكية تفحص القناة وتجمع المقاطع مع شرحها تلقائياً"""
    posts = []
    current_group = []
    
    # سيفحص البوت من الرسالة رقم 2 وحتى الرسالة 200 تلقائياً (ليغطي الـ 63 الحالية وأي شيء تضيفه مستقبلاً)
    # الفحص يتم على دفعات (Chunks) لأن التليجرام يسمح بطلب 100 رسالة كحد أقصى في المرة الواحدة
    chunk_size = 100
    for base_id in range(2, 200, chunk_size):
        ids_to_fetch = list(range(base_id, base_id + chunk_size))
        try:
            messages = bot.get_messages(chat_id=PRIVATE_CHANNEL, message_ids=ids_to_fetch)
            
            for msg in messages:
                if msg is None or msg.date is None:
                    continue  # يتخطى الرسائل المحذوفة أو الفارغة
                
                current_group.append(msg.message_id)
                
                # إذا واجه البوت رسالة نصية (الشرح)، فهذا يعني نهاية هذا المنشور
                if msg.content_type == 'text':
                    posts.append([current_group[0], current_group[-1]])
                    current_group = []  # تصفير المجموعة للبدء في المنشور التالي
                    
        except Exception as e:
            print(f"تنبيه أثناء الفحص التلقائي: {e}")
            break

    # إذا لم يجد شيئاً (كاحتياط لعدم توقف البوت) يضع المنشور الأول الافتراضي
    if not posts:
        posts = [[2, 3]]
        
    return posts

def send_random_clip():
    # 1. البوت يفحص القناة فوراً ويجلب القائمة المحدثة بالكامل
    posts_data = get_dynamic_posts()
    print(f"🔍 تم اكتشاف {len(posts_data)} منشور جاهز في المخزن.")
    
    # 2. اختيار منشور عشوائي
    selected_post = random.choice(posts_data)
    start_id = selected_post[0]
    end_id = selected_post[1]
    
    msg_ids = list(range(start_id, end_id + 1))
    
    try:
        # 3. نسخ المنشور كاملاً إلى القناة العامة كبلونة واحدة
        bot.copy_messages(
            chat_id=PUBLIC_CHANNEL,
            from_chat_id=PRIVATE_CHANNEL,
            message_ids=msg_ids
        )
        print(f"🚀 تم بنجاح نشر المنشور العشوائي من الرسالة {start_id} إلى {end_id}")
    except Exception as e:
        print(f"❌ حدث خطأ أثناء النشر: {e}")

# 4. ⏰ ضبط توقيت الحملة (كل 10 دقائق من الساعة 12 الليل بتوقيت الرياض)
scheduler = BackgroundScheduler(timezone="Asia/Riyadh")

# الفترة الأولى: من 12:00 منصف الليل وحتى 12:50 الليل
scheduler.add_job(send_random_clip, 'cron', hour=0, minute='0,10,20,30,40,50')

# الفترة الثانية: من 1:00 بعد منتصف الليل وحتى 1:30 الليل
scheduler.add_job(send_random_clip, 'cron', hour=1, minute='0,10,20,30')

scheduler.start()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
