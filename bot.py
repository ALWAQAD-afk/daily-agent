import os
import json
import random
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from google import genai

# ====================== الإعدادات ======================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

TIMEZONE = ZoneInfo("Asia/Amman")  # توقيت الأردن
PROFILE_FILE = "profile.json"
MEMORY_FILE = "memory.json"

# ====================== تحميل الملفات ======================
def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ====================== معلومات الوقت ======================
def get_current_context():
    now = datetime.now(TIMEZONE)
    days_ar = {
        "Monday": "الإثنين",
        "Tuesday": "الثلاثاء",
        "Wednesday": "الأربعاء",
        "Thursday": "الخميس",
        "Friday": "الجمعة",
        "Saturday": "السبت",
        "Sunday": "الأحد"
    }
    day_en = now.strftime("%A")
    day_ar = days_ar.get(day_en, day_en)
    time_str = now.strftime("%H:%M")
    date_str = now.strftime("%Y-%m-%d")
    return {
        "day_ar": day_ar,
        "day_en": day_en,
        "time": time_str,
        "date": date_str,
        "hour": now.hour
    }

# ====================== توليد الرسالة ======================
def generate_smart_message(profile, memory, context):
    client = genai.Client(api_key=GEMINI_API_KEY)

    known_facts = memory.get("known_facts", [])
    recent_topics = memory.get("recent_topics", [])
    progress_notes = memory.get("progress_notes", [])

    memory_text = ""
    if known_facts:
        memory_text += "حقائق أعرفها عنه:\n- " + "\n- ".join(known_facts) + "\n"
    if recent_topics:
        memory_text += "مواضيع حديثة تحدثنا عنها:\n- " + "\n- ".join(recent_topics[-5:]) + "\n"
    if progress_notes:
        memory_text += "ملاحظات عن تقدمه:\n- " + "\n- ".join(progress_notes[-5:]) + "\n"

    if not memory_text:
        memory_text = "لا أملك بعد معلومات كثيرة عنه. سأتعلم من خلال الحوار."

    hour = context["hour"]
    if 5 <= hour < 11:
        time_mood = "صباحية منشطة"
    elif 11 <= hour < 16:
        time_mood = "نهارية هادئة ومتابعة"
    elif 16 <= hour < 21:
        time_mood = "مسائية تشجيعية"
    else:
        time_mood = "ليلية هادئة ولطيفة"

    prompt = f"""
أنت وكيل ذكي شخصي وودود وحكيم اسمك "الوكيل اليومي".
تخاطب الشاب: {profile.get('name', 'الحارث')}.

معلومات ثابتة عنه فقط:
- التخصص: {profile.get('specialty', 'طالب شريعة')}
- اهتماماته الأساسية: {', '.join(profile.get('interests', []))}

اليوم: {context['day_ar']} ({context['date']}) الساعة تقريباً {context['time']} بتوقيت الأردن.
نبرة الرسالة المطلوبة: {time_mood}.

ذاكرتي الحالية عنه:
{memory_text}

=== التعليمات ===
1. اكتب رسالة قصيرة (3-6 جمل كحد أقصى)، طبيعية جداً، غير روبوتية، وكأنك صديق حكيم يتابع.
2. اجعل الرسالة مرتبطة باليوم الحالي إن أمكن (مثلاً واجب الإثنين، درس سيرة، جمعة...).
3. استخدم ما تعرفه من الذاكرة حتى تبدو متذكراً ومتابعاً حقيقياً.
4. نوع في الأسلوب: أحياناً سؤال مباشر، أحياناً تشجيع، أحياناً ملاحظة لطيفة، أحياناً تذكير خفيف.
5. لا تكرر نفس الجمل أو الأسئلة في كل مرة.
6. لا تذكر أنك ذكاء اصطناعي أو أنك ترسل من GitHub.
7. اجعل الرسالة تفتح باب الحوار (اسأل سؤالاً بسيطاً في النهاية غالباً).
8. إذا كانت الذاكرة فارغة تقريباً، قدم نفسك بلطف واسأل عن حاله أو عن أحد اهتماماته.

اكتب الرسالة فقط بدون أي مقدمات أو شرح.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"خطأ في Gemini: {e}")
        fallbacks = [
            f"صباح الخير يا {profile.get('name')}، كيف حالك اليوم؟",
            f"يا {profile.get('name')}، مرّ الوقت بسرعة.. كيف سير أمورك؟",
            f"هلا {profile.get('name')}، أين وصلت اليوم في وردك؟",
        ]
        return random.choice(fallbacks)

# ====================== إرسال الرسالة ======================
def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("مفاتيح تليجرام غير موجودة")
        return None

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=15)
        result = response.json()
        if not result.get("ok"):
            print(f"فشل إرسال تليجرام: {result}")
        return result
    except Exception as e:
        print(f"خطأ في الاتصال بتليجرام: {e}")
        return None

# ====================== التشغيل الرئيسي ======================
if __name__ == "__main__":
    print("بدء تشغيل الوكيل اليومي...")

    profile = load_json(PROFILE_FILE, {
        "name": "الحارث",
        "specialty": "طالب شريعة",
        "interests": ["التقنية", "حفظ المتون", "الأنكي"]
    })
    memory = load_json(MEMORY_FILE, {
        "last_updated": None,
        "known_facts": [],
        "recent_topics": [],
        "progress_notes": [],
        "conversation_style_preferences": []
    })

    context = get_current_context()
    print(f"اليوم: {context['day_ar']} - الساعة: {context['time']}")

    msg = generate_smart_message(profile, memory, context)
    print(f"الرسالة المولدة:\n{msg}\n")

    result = send_telegram_message(msg)
    if result and result.get("ok"):
        print("تم إرسال الرسالة بنجاح!")
    else:
        print("فشل إرسال الرسالة.")
