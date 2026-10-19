import os
import json
import random
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests
from google import genai

# ====================== الإعدادات ======================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

TIMEZONE = ZoneInfo("Asia/Amman")
PROFILE_FILE = "profile.json"
MEMORY_FILE = "memory.json"

# ====================== أدوات مساعدة ======================
def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_current_context():
    now = datetime.now(TIMEZONE)
    days_ar = {
        "Monday": "الإثنين", "Tuesday": "الثلاثاء", "Wednesday": "الأربعاء",
        "Thursday": "الخميس", "Friday": "الجمعة", "Saturday": "السبت", "Sunday": "الأحد"
    }
    day_en = now.strftime("%A")
    return {
        "day_ar": days_ar.get(day_en, day_en),
        "day_en": day_en,
        "time": now.strftime("%H:%M"),
        "date": now.strftime("%Y-%m-%d"),
        "hour": now.hour,
        "now": now
    }

# ====================== تليجرام ======================
def get_telegram_updates(offset=None, limit=20):
    """جلب آخر التحديثات من تليجرام"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {"limit": limit, "timeout": 0}
    if offset:
        params["offset"] = offset
    try:
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        if data.get("ok"):
            return data.get("result", [])
        print(f"خطأ getUpdates: {data}")
        return []
    except Exception as e:
        print(f"فشل جلب التحديثات: {e}")
        return []

def send_telegram_message(text, reply_to=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("مفاتيح تليجرام ناقصة")
        return None
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    try:
        r = requests.post(url, json=payload, timeout=15)
        result = r.json()
        if not result.get("ok"):
            print(f"فشل الإرسال: {result}")
        return result
    except Exception as e:
        print(f"خطأ إرسال: {e}")
        return None

def extract_user_messages(updates, chat_id):
    """استخراج رسائل المستخدم فقط من التحديثات"""
    messages = []
    for upd in updates:
        msg = upd.get("message") or upd.get("edited_message")
        if not msg:
            continue
        if str(msg.get("chat", {}).get("id")) != str(chat_id):
            continue
        if msg.get("from", {}).get("is_bot"):
            continue
        text = msg.get("text") or msg.get("caption")
        if text:
            messages.append({
                "update_id": upd["update_id"],
                "message_id": msg["message_id"],
                "text": text.strip(),
                "date": msg.get("date")
            })
    return messages

# ====================== الذكاء (Gemini) ======================
def call_gemini(prompt, model="gemini-2.0-flash"):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text.strip()
    except Exception as e:
        print(f"خطأ Gemini: {e}")
        return None

def process_conversation(profile, memory, context, user_messages):
    """
    يعالج رسائل المستخدم:
    - يستخرج حقائق وملاحظات
    - يولد رداً مناسباً
    يرجع: (الرد, الذاكرة المحدثة)
    """
    if not user_messages:
        return None, memory

    # نأخذ آخر 5 رسائل كحد أقصى
    recent = user_messages[-5:]
    conversation_text = "\n".join([f"- {m['text']}" for m in recent])

    known_facts = memory.get("known_facts", [])
    progress_notes = memory.get("progress_notes", [])
    recent_topics = memory.get("recent_topics", [])

    prompt = f"""
أنت "الوكيل اليومي"، صديق حكيم وودود وذكي للشاب {profile.get('name')}.
تخصصه: {profile.get('specialty')}.
اهتماماته: {', '.join(profile.get('interests', []))}.

اليوم: {context['day_ar']} الساعة {context['time']} بتوقيت الأردن.

=== الذاكرة الحالية ===
حقائق معروفة:
{chr(10).join(['- ' + f for f in known_facts]) or '- لا يوجد بعد'}

ملاحظات التقدم:
{chr(10).join(['- ' + f for f in progress_notes[-8:]]) or '- لا يوجد'}

مواضيع حديثة:
{chr(10).join(['- ' + f for f in recent_topics[-6:]]) or '- لا يوجد'}

=== آخر رسائل منه ===
{conversation_text}

=== المطلوب منك ===
1. استخرج أي معلومات جديدة مهمة (حقائق عن حياته، تقدمه في الحفظ/الأنكي/الدراسة، مشاعره، تفضيلاته...).
2. استخرج ملاحظات تقدم إن وجدت.
3. حدد المواضيع الرئيسية في هذا الحوار.
4. اكتب رداً طبيعياً وقصيراً (3-7 جمل) كصديق يتابع بصدق، مرتبط بما قاله، ويفتح باب الاستمرار إن ناسب.

أرجع الرد بهذا الشكل بالضبط (JSON):

{{
  "new_facts": ["حقيقة 1", "حقيقة 2"],
  "progress_notes": ["ملاحظة تقدم 1"],
  "topics": ["موضوع 1", "موضوع 2"],
  "reply": "الرد هنا..."
}}
"""

    raw = call_gemini(prompt)
    if not raw:
        return "وصلتني رسالتك، بس صار عندي مشكلة بسيطة. حاول مرة ثانية بعد شوي 😊", memory

    # محاولة استخراج JSON
    try:
        # تنظيف بسيط
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        data = json.loads(raw)
    except Exception:
        # لو فشل JSON نعتبر كل النص رد
        return raw, memory

    # تحديث الذاكرة
    new_facts = data.get("new_facts", [])
    new_progress = data.get("progress_notes", [])
    new_topics = data.get("topics", [])

    for f in new_facts:
        if f and f not in memory["known_facts"]:
            memory["known_facts"].append(f)

    for p in new_progress:
        if p:
            memory["progress_notes"].append(p)

    for t in new_topics:
        if t and t not in memory["recent_topics"]:
            memory["recent_topics"].append(t)

    # نحد من الطول
    memory["known_facts"] = memory["known_facts"][-25:]
    memory["progress_notes"] = memory["progress_notes"][-20:]
    memory["recent_topics"] = memory["recent_topics"][-15:]
    memory["last_updated"] = context["date"] + " " + context["time"]

    reply = data.get("reply") or "وصلتني رسالتك 👍"
    return reply, memory

def generate_proactive_message(profile, memory, context):
    """رسالة استباقية ذكية عندما ما فيه حوار حديث"""
    known_facts = memory.get("known_facts", [])
    progress_notes = memory.get("progress_notes", [])
    recent_topics = memory.get("recent_topics", [])

    memory_text = ""
    if known_facts:
        memory_text += "حقائق أعرفها:\n- " + "\n- ".join(known_facts[-10:]) + "\n"
    if progress_notes:
        memory_text += "آخر ملاحظات التقدم:\n- " + "\n- ".join(progress_notes[-6:]) + "\n"
    if recent_topics:
        memory_text += "مواضيع حديثة:\n- " + "\n- ".join(recent_topics[-5:]) + "\n"
    if not memory_text:
        memory_text = "ما زلت أتعلم عنه."

    hour = context["hour"]
    if 5 <= hour < 11:
        mood = "صباحية منشطة ولطيفة"
    elif 11 <= hour < 16:
        mood = "نهارية هادئة ومتابعة"
    elif 16 <= hour < 21:
        mood = "مسائية تشجيعية ودافئة"
    else:
        mood = "ليلية هادئة ورفيقة"

    prompt = f"""
أنت "الوكيل اليومي"، صديق شخصي حكيم وودود للشاب {profile.get('name')} (طالب شريعة مهتم بالتقنية والحفظ والأنكي).

اليوم: {context['day_ar']} ({context['date']}) الساعة {context['time']} بتوقيت الأردن.
النبرة المطلوبة: {mood}.

=== ذاكرتي عنه ===
{memory_text}

اكتب رسالة قصيرة جداً (3-6 جمل)، طبيعية، غير روبوتية، كأنها من صديق يتابع بصدق.
- اربطها باليوم إن أمكن.
- استخدم الذاكرة حتى تبدو متذكراً.
- نوع الأسلوب (سؤال، تشجيع، ملاحظة، تذكير خفيف...).
- افتح باب الحوار بسؤال بسيط في النهاية غالباً.
- لا تذكر أنك ذكاء اصطناعي.

الرسالة فقط:
"""
    msg = call_gemini(prompt)
    if not msg:
        fallbacks = [
            f"هلا {profile.get('name')}، كيف أمورك اليوم؟",
            f"يا {profile.get('name')}، وين وصلت اليوم؟",
            f"صباح الخير يا وحش، كيف السير؟"
        ]
        msg = random.choice(fallbacks)
    return msg

# ====================== التشغيل الرئيسي ======================
if __name__ == "__main__":
    print("=" * 50)
    print("بدء تشغيل الوكيل اليومي الكامل...")
    print("=" * 50)

    profile = load_json(PROFILE_FILE, {
        "name": "الحارث",
        "specialty": "طالب شريعة",
        "interests": ["التقنية", "حفظ المتون", "الأنكي"]
    })
    memory = load_json(MEMORY_FILE, {
        "last_updated": None,
        "last_update_id": 0,
        "known_facts": [],
        "recent_topics": [],
        "progress_notes": [],
        "conversation_style_preferences": []
    })

    # تأكد من وجود الحقول
    for key in ["known_facts", "recent_topics", "progress_notes", "conversation_style_preferences"]:
        if key not in memory:
            memory[key] = []
    if "last_update_id" not in memory:
        memory["last_update_id"] = 0

    context = get_current_context()
    print(f"اليوم: {context['day_ar']} | الساعة: {context['time']}")

    # 1. جلب الرسائل الجديدة
    offset = memory.get("last_update_id", 0) + 1 if memory.get("last_update_id") else None
    updates = get_telegram_updates(offset=offset)
    user_messages = extract_user_messages(updates, TELEGRAM_CHAT_ID)

    print(f"عدد الرسائل الجديدة من المستخدم: {len(user_messages)}")

    replied = False

    if user_messages:
        # فيه حوار → نرد ونحدث الذاكرة
        print("يوجد رسائل جديدة → معالجة الحوار...")
        reply, memory = process_conversation(profile, memory, context, user_messages)
        if reply:
            # نحدث last_update_id
            memory["last_update_id"] = max(m["update_id"] for m in user_messages)
            send_telegram_message(reply)
            print("تم إرسال الرد على المستخدم.")
            replied = True
    else:
        print("لا توجد رسائل جديدة.")

    # 2. لو ما ردينا (أو حتى لو ردينا)، نرسل رسالة استباقية أحياناً؟
    # حالياً: نرسل استباقية فقط لو ما كان فيه حوار حديث
    if not replied:
        print("إرسال رسالة استباقية...")
        proactive = generate_proactive_message(profile, memory, context)
        send_telegram_message(proactive)
        print("تم إرسال الرسالة الاستباقية.")

    # 3. حفظ الذاكرة
    memory["last_updated"] = f"{context['date']} {context['time']}"
    save_json(MEMORY_FILE, memory)
    print("تم حفظ memory.json")

    print("=" * 50)
    print("انتهى تشغيل الوكيل.")
    print("=" * 50)
