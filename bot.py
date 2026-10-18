import os
import requests
from google import genai

# جلب المفاتيح من بيئة العمل السحابية
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def generate_smart_message():
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = """
    أنت وكيل ذكي وموجه شخصي حكيم وودود للشاب (الوقّاد)، طالب شريعة ومهتم بالتقنية.
    لديه أهداف وجدول: واجب يوم الإثنين، درس سيرة أيام (الإثنين والأربعاء والخميس)، ودرس الجمعة فجراً، ومراجعة أنكي وحفظ المتون.
    اكتب له رسالة قصيرة، ذكية، تحفيزية، وغير روبوتية تسأله عن تقدمه وتفتتح الحوار بأسلوب لطيف.
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    return response.json()

if __name__ == "__main__":
    missing = []
    if not TELEGRAM_BOT_TOKEN: missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID: missing.append("TELEGRAM_CHAT_ID")
    if not GEMINI_API_KEY: missing.append("GEMINI_API_KEY")
    
    if missing:
        print(f"خطأ حرج: المتغيرات التالية مفقودة أو لم يتم قراءتها: {', '.join(missing)}")
        exit(1)
        
    msg = generate_smart_message()
    send_telegram_message(msg)
    print("تم إرسال الرسالة التفاعلية بنجاح!")
