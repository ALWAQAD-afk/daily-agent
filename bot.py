import os
import requests
from google import genai

# قراءة المفاتيح من إعدادات GitHub Secrets
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def generate_smart_message():
    # استخدام النموذج الصحيح والحديث
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = """
    أنت وكيل ذكي وموجه شخصي حكيم وودود للشاب (الحارث)، طالب شريعة ومهتم بالتقنية.
    لديه أهداف وجدول: واجب يوم الإثنين، درس سيرة أيام (الإثنين والأربعاء والخميس)، ودرس الجمعة فجراً، ومراجعة أنكي وحفظ المتون.
    اكتب له رسالة قصيرة، ذكية، تحفيزية، وغير روبوتية تسأله عن تقدمه وتفتتح الحوار بأسلوب لطيف.
    إذا كانت رسالتك تصلح كتذكير مفاجئ، اسأله: "هل أنجزت وردك اليوم؟" أو "أين وصلت في الأنكي؟".
    """
    
    response = client.models.generate_content(
        model="gemini-2.0-flash", 
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
    print("تم إرسال الرسالة المبادرة بنجاح!")
