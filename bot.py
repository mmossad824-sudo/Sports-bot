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
        
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
        
    # Check if we should use Vercel proxy to bypass Hugging Face outbound blocks
    # Use proxy by default if WEBSITE_URL is configured and is not local
    use_proxy = False
    if WEBSITE_URL and "localhost" not in WEBSITE_URL and "127.0.0.1" not in WEBSITE_URL and "your-vercel-domain" not in WEBSITE_URL:
        use_proxy = True
        
    if use_proxy:
        url = f"{WEBSITE_URL.rstrip('/')}/api/telegram_proxy"
        payload["token"] = BOT_TOKEN
        print(f"[Telegram Client] Routing message through Vercel proxy: {url}")
    else:
        url = f"{TELEGRAM_API_URL}/bot{BOT_TOKEN}/sendMessage"
        print(f"[Telegram Client] Sending message directly to Telegram API: {url}")
        
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            print("Telegram message sent successfully.")
            return True
        else:
            print(f"Failed to send Telegram message: {response.text}")
            # If proxy failed, fallback directly
            if use_proxy:
                fallback_url = f"{TELEGRAM_API_URL}/bot{BOT_TOKEN}/sendMessage"
                print(f"[Telegram Client] Proxy failed. Trying direct fallback to Telegram API...")
                payload.pop("token", None)
                fb_resp = requests.post(fallback_url, json=payload, timeout=10)
                return fb_resp.status_code == 200
            return False
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        # Direct fallback on exception
        if use_proxy:
            try:
                fallback_url = f"{TELEGRAM_API_URL}/bot{BOT_TOKEN}/sendMessage"
                print(f"[Telegram Client] Proxy exception. Trying direct fallback to Telegram API...")
                payload.pop("token", None)
                fb_resp = requests.post(fallback_url, json=payload, timeout=10)
                return fb_resp.status_code == 200
            except Exception as ex:
                print(f"Fallback failed: {ex}")
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

def check_and_send_alerts():
    if not os.path.exists(DB_PATH):
        print("Database file does not exist.")
        return
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    from datetime import datetime, timedelta
    cairo_now = datetime.utcnow() + timedelta(hours=3)
    cairo_today = cairo_now.strftime("%Y-%m-%d")
    
    # Select all active matches for today
    cursor.execute("""
        SELECT * FROM matches 
        WHERE match_date = ? OR match_date IS NULL
    """, (cairo_today,))
    matches = cursor.fetchall()
    
    for m in matches:
        match_id = m['id']
        team_a = m['teamA']
        team_b = m['teamB']
        tournament = m['tournament']
        status = m['status']
        score_a = m['scoreA']
        score_b = m['scoreB']
        time_str = m['time']
        
        # Safe reading of values
        start_sent = m['telegram_start_sent'] if 'telegram_start_sent' in m.keys() else 0
        half_sent = m['telegram_half_sent'] if 'telegram_half_sent' in m.keys() else 0
        end_sent = m['telegram_end_sent'] if 'telegram_end_sent' in m.keys() else 0
        last_score_a = m['last_telegram_scoreA'] if 'last_telegram_scoreA' in m.keys() else None
        last_score_b = m['last_telegram_scoreB'] if 'last_telegram_scoreB' in m.keys() else None
        
        # 1. Start Alert (15 minutes before match start, or when it starts)
        should_send_start = False
        if not start_sent:
            if status == 'جارية الآن' or 'الشوط' in status:
                should_send_start = True
            elif status == 'لم تبدأ' and time_str and ':' in time_str:
                try:
                    match_hour, match_min = map(int, time_str.split(':'))
                    match_dt = cairo_now.replace(hour=match_hour, minute=match_min, second=0, microsecond=0)
                    diff = (match_dt - cairo_now).total_seconds()
                    # 15 minutes = 900 seconds. 
                    # If match starts in <= 15 minutes (900 seconds) and we haven't passed start time by more than 15 mins
                    if -900 <= diff <= 900:
                        should_send_start = True
                except Exception as ex:
                    print(f"Error parsing start time for alert: {ex}")
                    
        if should_send_start:
            print(f"[Telegram Alert] Sending start alert for {team_a} VS {team_b}...")
            text = (
                f"🚨 <b>مباراة مرتقبة تبدأ قريباً!</b>\n\n"
                f"🏆 {tournament}\n"
                f"⚔️ <b>{team_a} 🆚 {team_b}</b>\n\n"
                f"⏰ التوقيت: {time_str} (بتوقيت مصر)\n"
                f"📺 البث المباشر متوفر الآن بجودة عالية وبدون تقطيع!\n"
                f"اضغط على زر المشاهدة أدناه للمتابعة مباشرة 👇"
            )
            reply_markup = {
                "inline_keyboard": [
                    [{"text": "📺 شاهد المباراة بث مباشر الآن", "url": WEBSITE_URL}]
                ]
            }
            if send_telegram_message(text, reply_markup=reply_markup):
                conn_write = sqlite3.connect(DB_PATH)
                cursor_write = conn_write.cursor()
                cursor_write.execute("UPDATE matches SET telegram_start_sent = 1 WHERE id = ?", (match_id,))
                conn_write.commit()
                conn_write.close()
                
        # 2. Goal Alerts (if match is live, check if score changed)
        is_live = (status == 'جارية الآن' or 'الشوط' in status)
        if is_live and last_score_a is not None and last_score_b is not None:
            try:
                curr_a = int(score_a) if score_a.isdigit() else 0
                curr_b = int(score_b) if score_b.isdigit() else 0
                prev_a = int(last_score_a) if str(last_score_a).isdigit() else 0
                prev_b = int(last_score_b) if str(last_score_b).isdigit() else 0
                
                if curr_a > prev_a or curr_b > prev_b:
                    scorer_team = team_a if curr_a > prev_a else team_b
                    print(f"[Telegram Alert] Goal scored! {scorer_team} scored in {team_a} VS {team_b} ({score_a}-{score_b})")
                    
                    text = (
                        f"⚽️ <b>جووووول! هدف جديد في المباراة!</b>\n\n"
                        f"🏆 {tournament}\n"
                        f"⚔️ <b>{team_a} {score_a} - {score_b} {team_b}</b>\n\n"
                        f"📺 تابع الهدف ومجريات البث المباشر مباشرة 👇"
                    )
                    reply_markup = {
                        "inline_keyboard": [
                            [{"text": "📺 شاهد الهدف والبث المباشر", "url": WEBSITE_URL}]
                        ]
                    }
                    send_telegram_message(text, reply_markup=reply_markup)
            except Exception as e:
                print(f"Error processing goal alerts: {e}")
                
        # Update last score values for live matches so next check detects score changes
        if is_live:
            conn_write = sqlite3.connect(DB_PATH)
            cursor_write = conn_write.cursor()
            cursor_write.execute("UPDATE matches SET last_telegram_scoreA = ?, last_telegram_scoreB = ? WHERE id = ?", (score_a, score_b, match_id))
            conn_write.commit()
            conn_write.close()
            
        # 3. Halftime Alert (status is 'بين الشوطين')
        is_halftime = (status == 'بين الشوطين' or 'بين الشوطين' in status)
        if is_halftime and not half_sent:
            print(f"[Telegram Alert] Sending halftime alert for {team_a} VS {team_b}...")
            text = (
                f"⏸️ <b>نهاية الشوط الأول (الاستراحة)</b>\n\n"
                f"🏆 {tournament}\n"
                f"⚔️ <b>{team_a} {score_a} 🆚 {score_b} {team_b}</b>\n\n"
                f"📺 لمتابعة الشوط الثاني ومجريات البث المباشر 👇"
            )
            reply_markup = {
                "inline_keyboard": [
                    [{"text": "📺 تابع البث المباشر الآن", "url": WEBSITE_URL}]
                ]
            }
            if send_telegram_message(text, reply_markup=reply_markup):
                conn_write = sqlite3.connect(DB_PATH)
                cursor_write = conn_write.cursor()
                cursor_write.execute("UPDATE matches SET telegram_half_sent = 1 WHERE id = ?", (match_id,))
                conn_write.commit()
                conn_write.close()
                
        # 4. End Alert (status is 'انتهت')
        is_ended = (status == 'انتهت' or 'انتهت' in status)
        if is_ended and not end_sent:
            print(f"[Telegram Alert] Sending end-of-match alert for {team_a} VS {team_b}...")
            text = (
                f"🏁 <b>نهاية المباراة! النتيجة النهائية</b>\n\n"
                f"🏆 {tournament}\n"
                f"⚔️ <b>{team_a} {score_a} 🆚 {score_b} {team_b}</b>\n\n"
                f"🎬 شاهد أهداف وملخص المباراة الآن على موقعنا 👇"
            )
            reply_markup = {
                "inline_keyboard": [
                    [{"text": "🎬 شاهد أهداف وملخص المباراة", "url": WEBSITE_URL}]
                ]
            }
            if send_telegram_message(text, reply_markup=reply_markup):
                conn_write = sqlite3.connect(DB_PATH)
                cursor_write = conn_write.cursor()
                cursor_write.execute("UPDATE matches SET telegram_end_sent = 1 WHERE id = ?", (match_id,))
                conn_write.commit()
                conn_write.close()
                
    conn.close()

if __name__ == "__main__":
    print(format_daily_schedule())
