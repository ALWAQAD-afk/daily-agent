import os
import requests
from google import genai

# ضع معلوماتك هنا مباشرة لحل مشكلة قراءة المتغيرات السحابية نهائياً
TELEGRAM_BOT_TOKEN = "8998558070:AAF_fYr2gym7JtX2TieGxnh4WeP1rIQ71ns"
TELEGRAM_CHAT_ID = "7991076455"
GEMINI_API_KEY = "AQ.Ab8RN6K-mN5KAExbn5pl9sR6A4P2VTLKBq-brDtEY4L4_F1AUg"

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
    msg = generate_smart_message()
    send_telegram_message(msg)
    print("تم إرسال الرسالة التفاعلية بنجاح!")
