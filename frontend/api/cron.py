from http.server import BaseHTTPRequestHandler
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json

# Environment Variables from Vercel (Default values or placeholders if not set)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8979671229:AAGyVHMlWDuHi7OcQRp13wqTvz2jEBfRa2M")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@yalla_shoottoday")
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://yalla-shoot-today.vercel.app")

def send_telegram_message(text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
        
    try:
        response = requests.post(url, json=payload, timeout=15)
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def scrape_and_format():
    now = datetime.now()
    date_str = f"{now.month}/{now.day}/{now.year}"
    url = f"https://www.yallakora.com/match-center/?date={date_str}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return "❌ خطأ في جلب البيانات من المصدر."
            
        soup = BeautifulSoup(response.content, 'html.parser')
        tournaments = soup.find_all('div', class_='matchCard')
        
        if not tournaments:
            return "📅 لا توجد مباريات اليوم."
            
        by_tour = {}
        for tour in tournaments:
            tour_title = tour.find('a', class_='tourTitle') or tour.find('div', class_='title')
            tour_name = tour_title.text.strip() if tour_title else "بطولة غير معروفة"
            
            match_ul = tour.find('div', class_='ul')
            if not match_ul:
                continue
                
            match_rows = match_ul.find_all('div', class_='liItem')
            if not match_rows:
                continue
                
            by_tour[tour_name] = []
            
            for row in match_rows:
                channel_tag = row.find('div', class_='channel')
                channel = channel_tag.text.strip() if channel_tag else ""
                
                status_tag = row.find('div', class_='matchStatus')
                status = status_tag.text.strip() if status_tag else "لم تبدأ"
                
                team_a = row.find('div', class_='teamA')
                team_a_name = team_a.find('p').text.strip() if team_a and team_a.find('p') else "فريق أ"
                
                team_b = row.find('div', class_='teamB')
                team_b_name = team_b.find('p').text.strip() if team_b and team_b.find('p') else "فريق ب"
                
                score_a = "-"
                score_b = "-"
                match_time = "-"
                
                result_div = row.find('div', class_='MResult')
                if result_div:
                    scores = result_div.find_all('span', class_='score')
                    if len(scores) >= 2:
                        score_a = scores[0].text.strip()
                        score_b = scores[1].text.strip()
                    
                    time_span = result_div.find('span', class_='time')
                    if time_span:
                        match_time = time_span.text.strip()
                
                classes = row.get('class', [])
                if 'finish' in classes:
                    status_desc = "انتهت"
                elif 'live' in classes:
                    status_desc = "جارية الآن"
                elif 'future' in classes:
                    status_desc = "لم تبدأ"
                else:
                    status_desc = status
                    
                by_tour[tour_name].append((team_a_name, team_b_name, score_a, score_b, match_time, status_desc, channel))
                
        msg = f"📅 <b>جدول مباريات اليوم ({datetime.now().strftime('%Y-%m-%d')})</b>\n\n"
        for tour, matches in by_tour.items():
            msg += f"🏆 <b>{tour}</b>:\n"
            for team_a, team_b, score_a, score_b, time_str, status_desc, channel in matches:
                channel_info = f" | 📺 {channel}" if channel else ""
                status_info = f" ({status_desc})" if status_desc != "لم تبدأ" else ""
                score_info = f" [{score_a} - {score_b}]" if status_desc != "لم تبدأ" else ""
                msg += f"  🔹 {team_a} 🆚 {team_b}{score_info}\n  ⏰ {time_str}{channel_info}{status_info}\n\n"
                
        msg += f"🔗 تابع المباريات مباشرة وبدون تقطيع على موقعنا:\n{WEBSITE_URL}"
        return msg
    except Exception as e:
        return f"❌ خطأ: {str(e)}"

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Scrape and broadcast
        text = scrape_and_format()
        reply_markup = {
            "inline_keyboard": [
                [{"text": "📺 مشاهدة المباريات بث مباشر", "url": WEBSITE_URL}]
            ]
        }
        success = send_telegram_message(text, reply_markup=reply_markup)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response_data = {
            "status": "success" if success else "failed",
            "message": "Broadcast sent to Telegram" if success else "Failed to send to Telegram",
            "channel": CHANNEL_ID
        }
        self.wfile.write(json.dumps(response_data).encode('utf-8'))
