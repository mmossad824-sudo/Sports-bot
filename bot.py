import os
import requests
import sqlite3
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")
DB_PATH = os.path.join(os.path.dirname(__file__), "matches.db")
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://your-vercel-domain.vercel.app")
TELEGRAM_API_URL = os.getenv("TELEGRAM_API_URL", "https://api.telegram.org").rstrip('/')

def send_telegram_message(text, parse_mode="HTML", reply_markup=None):
    if not BOT_TOKEN or not CHANNEL_ID:
        print("Telegram BOT_TOKEN or CHANNEL_ID not configured.")
        return False
        
    url = f"{TELEGRAM_API_URL}/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
        
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("Telegram message sent successfully.")
            return True
        else:
            print(f"Failed to send Telegram message: {response.text}")
            return False
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return False

def format_daily_schedule():
    if not os.path.exists(DB_PATH):
        return "لا توجد مباريات مسجلة اليوم."
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Select all matches for today
    cursor.execute("SELECT tournament, teamA, teamB, time, status, channel FROM matches")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return "📅 لا توجد مباريات مجدولة لليوم."
        
    # Group matches by tournament
    by_tour = {}
    for tour, team_a, team_b, time_str, status, channel in rows:
        if tour not in by_tour:
            by_tour[tour] = []
        by_tour[tour].append((team_a, team_b, time_str, status, channel))
        
    msg = f"📅 <b>جدول مباريات اليوم ({datetime.now().strftime('%Y-%m-%d')})</b>\n\n"
    
    for tour, matches in by_tour.items():
        msg += f"🏆 <b>{tour}</b>:\n"
        for team_a, team_b, time_str, status, channel in matches:
            channel_info = f" | 📺 {channel}" if channel else ""
            status_info = f" ({status})" if status != "لم تبدأ" else ""
            msg += f"  🔹 {team_a} 🆚 {team_b}\n  ⏰ {time_str}{channel_info}{status_info}\n\n"
            
    msg += f"🔗 تابع المباريات مباشرة على موقعنا:\n{WEBSITE_URL}"
    return msg

def broadcast_schedule():
    text = format_daily_schedule()
    # Add a clean inline button to open the website
    reply_markup = {
        "inline_keyboard": [
            [{"text": "📺 مشاهدة المباريات بث مباشر", "url": WEBSITE_URL}]
        ]
    }
    return send_telegram_message(text, reply_markup=reply_markup)

def send_live_alert(team_a, team_b, tournament, match_url_slug):
    match_link = f"{WEBSITE_URL}/match?id={match_url_slug}"
    text = (
        f"🚨 <b>مباراة مرتقبة تبدأ الآن!</b>\n\n"
        f"🏆 {tournament}\n"
        f"⚔️ <b>{team_a} 🆚 {team_b}</b>\n\n"
        f"📺 البث المباشر جاهز الآن بجودة عالية وبدون تقطيع!\n"
        f"اضغط على الرابط أدناه للمشاهدة مباشرة 👇"
    )
    reply_markup = {
        "inline_keyboard": [
            [{"text": "▶️ شاهد المباراة الآن", "url": match_link}]
        ]
    }
    return send_telegram_message(text, reply_markup=reply_markup)

if __name__ == "__main__":
    # Test format
    print(format_daily_schedule())
