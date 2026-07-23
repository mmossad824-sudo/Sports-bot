import os
import requests
import sqlite3
from datetime import datetime, timedelta

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")
DB_PATH = os.path.join(os.path.dirname(__file__), "matches.db")
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://your-vercel-domain.vercel.app")
TELEGRAM_API_URL = os.getenv("TELEGRAM_API_URL", "https://api.telegram.org").rstrip('/')
SPONSOR_URL = "https://www.profitablecpmrate.com/e4480b4a0a4ef0a7e842009f7c505039"
FB_PAGE_TOKEN = os.getenv("FB_PAGE_TOKEN", "")
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "1183659124839160")

# ─── FILTERS ──────────────────────────────────────────────────────────────────
# Only football. Only these leagues.
ALLOWED_TOURNAMENTS = [
    # Big 5 European
    "الدوري الإنجليزي", "الدوري الممتاز", "البريميرليغ", "premier league",
    "الدوري الإسباني", "لا ليغا", "la liga",
    "الدوري الإيطالي", "سيريا", "serie a",
    "الدوري الألماني", "بوندسليغا", "bundesliga",
    "الدوري الفرنسي", "ليغ 1", "ligue 1",
    # UCL/UEL/UECL
    "دوري أبطال أوروبا", "دوري أبطال", "champions league",
    "الدوري الأوروبي", "europa league",
    "دوري المؤتمر", "conference league",
    # Saudi
    "الدوري السعودي", "دوري روشن", "الدوري السعودي للمحترفين",
    # Egyptian
    "الدوري المصري", "الدوري المصري الممتاز",
    # Cups related to these leagues
    "كأس مصر", "كأس خادم الحرمين", "كأس الملك",
    "كأس الاتحاد الإنجليزي", "كأس ملك إسبانيا", "كأس إيطاليا",
    # World events
    "كأس العالم", "كأس العالم للأندية",
]

# Exclude non-football sports keywords
EXCLUDED_SPORTS = [
    "كرة السلة", "basketball", "tennis", "تنس", "كرة طائرة", "volleyball",
    "handball", "كرة يد", "rugby", "رغبي", "cricket", "كريكيت",
    "baseball", "بيسبول", "مصارعة", "boxing", "ملاكمة",
    "سباحة", "swimming", "atletismo", "ألعاب قوى",
]

def is_allowed_match(tournament: str, team_a: str = "", team_b: str = "") -> bool:
    t = tournament.lower()
    # Reject known non-football sports
    for excluded in EXCLUDED_SPORTS:
        if excluded.lower() in t:
            return False
    # Must match one of the allowed tournaments
    for allowed in ALLOWED_TOURNAMENTS:
        if allowed.lower() in t:
            return True
    return False


# ─── EMOJI HELPERS ────────────────────────────────────────────────────────────
def get_tournament_emoji(tour_name):
    t = tour_name.lower()
    if "إنجليزي" in t or "انجليزي" in t or "بريميرليغ" in t: return "🏴󠁧󠁢󠁥󠁮󠁧󠁿"
    if "إسباني" in t or "اسباني" in t or "ليغا" in t: return "🇪🇸"
    if "إيطالي" in t or "ايطالي" in t or "سيريا" in t: return "🇮🇹"
    if "فرنسي" in t or "ليغ" in t: return "🇫🇷"
    if "ألماني" in t or "الماني" in t or "بوندس" in t: return "🇩🇪"
    if "سعودي" in t or "روشن" in t: return "🇸🇦"
    if "مصر" in t: return "🇪🇬"
    if "دوري أبطال" in t or "ابطال اوروبا" in t or "champions" in t: return "⭐🏆"
    if "أوروبي" in t or "europa" in t: return "🇪🇺"
    if "مؤتمر" in t or "conference" in t: return "🌍"
    if "كأس العالم" in t: return "🏆🌍"
    if "أندية" in t: return "🏆⚽"
    return "⚽"

def get_team_flag(team_name):
    name = team_name.strip()
    flags = {
        "المغرب": "🇲🇦", "البرازيل": "🇧🇷", "الأرجنتين": "🇦🇷", "الارجنتين": "🇦🇷",
        "فرنسا": "🇫🇷", "إسبانيا": "🇪🇸", "اسبانيا": "🇪🇸", "إنجلترا": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
        "انجلترا": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "ألمانيا": "🇩🇪", "المانيا": "🇩🇪", "إيطاليا": "🇮🇹",
        "البرتغال": "🇵🇹", "هولندا": "🇳🇱", "بلجيكا": "🇧🇪", "كرواتيا": "🇭🇷",
        "السعودية": "🇸🇦", "مصر": "🇪🇬", "تونس": "🇹🇳", "الجزائر": "🇩🇿",
        "العراق": "🇮🇶", "السنغال": "🇸🇳", "كوريا": "🇰🇷", "اليابان": "🇯🇵",
        "أمريكا": "🇺🇸", "الولايات المتحدة": "🇺🇸", "أستراليا": "🇦🇺", "تركيا": "🇹🇷",
    }
    for key, flag in flags.items():
        if key in name:
            return flag
    # Club emoji shortcuts
    clubs = {
        "ريال مدريد": "⚪", "برشلونة": "🔵🔴", "ليفربول": "🔴",
        "مانشستر سيتي": "🩵", "مانشستر يونايتد": "🔴", "أرسنال": "🔴⚪",
        "ارسنال": "🔴⚪", "تشيلسي": "🔵", "توتنهام": "⚪",
        "بايرن": "🔴", "باريس": "🔵🔴", "يوفنتوس": "⚫⚪",
        "إنتر": "⚫🔵", "انتر": "⚫🔵", "ميلان": "🔴⚫",
        "الهلال": "🔵", "النصر": "🟡", "الاتحاد": "🟡⚫",
        "الأهلي": "🔴", "الاهلي": "🔴", "الزمالك": "⚪🔴",
        "بيراميدز": "🔵",
    }
    for key, emoji in clubs.items():
        if key in name:
            return emoji
    return "⚽"


# ─── TELEGRAM API ─────────────────────────────────────────────────────────────
def send_telegram_api(method, payload):
    if not BOT_TOKEN or not CHANNEL_ID:
        print("Telegram BOT_TOKEN or CHANNEL_ID not configured.")
        return None

    if "chat_id" not in payload:
        payload["chat_id"] = CHANNEL_ID

    use_proxy = (
        WEBSITE_URL and
        "localhost" not in WEBSITE_URL and
        "127.0.0.1" not in WEBSITE_URL and
        "your-vercel-domain" not in WEBSITE_URL
    )

    if use_proxy:
        url = f"{WEBSITE_URL.rstrip('/')}/api/telegram_proxy"
        payload["token"] = BOT_TOKEN
        payload["method"] = method
    else:
        url = f"{TELEGRAM_API_URL}/bot{BOT_TOKEN}/{method}"

    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            try:
                res_data = response.json()
                if res_data.get("ok"):
                    return res_data
            except Exception:
                pass
            return {"ok": True}
        else:
            print(f"[Telegram] Failed {method}: {response.text[:200]}")
            if use_proxy:
                # Direct fallback
                payload.pop("token", None)
                payload.pop("method", None)
                try:
                    fb = requests.post(f"{TELEGRAM_API_URL}/bot{BOT_TOKEN}/{method}", json=payload, timeout=10)
                    if fb.status_code == 200:
                        return fb.json()
                except Exception:
                    pass
            return None
    except Exception as e:
        print(f"[Telegram] Exception {method}: {e}")
        return None


def send_message_and_get_id(text, reply_markup=None) -> int | None:
    """Send message, return message_id if successful."""
    payload = {
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    res = send_telegram_api("sendMessage", payload)
    if res and isinstance(res, dict):
        result = res.get("result", {})
        return result.get("message_id") if isinstance(result, dict) else None
    return None


def send_telegram_message(text, parse_mode="HTML", reply_markup=None):
    return send_message_and_get_id(text, reply_markup) is not None


def pin_telegram_message(message_id):
    return send_telegram_api("pinChatMessage", {
        "message_id": message_id,
        "disable_notification": True,
    })


def send_telegram_poll(question, options):
    return send_telegram_api("sendPoll", {
        "question": question,
        "options": options,
        "is_anonymous": False,
    })

def post_fb_start_alert(team_a, team_b, tournament, time_str):
    if not FB_PAGE_TOKEN or not FB_PAGE_ID:
        return
    fb_text = (
        f"🔥 بدأت الآن القمة المنتظرة! 🔥\n\n"
        f"🏆 {tournament}\n"
        f"⚔️ {team_a} 🆚 {team_b}\n"
        f"⏰ {time_str}\n\n"
        f"🤔 من سيفوز في مباراة اليوم؟ شاركونا توقعاتكم في التعليقات 👇\n\n"
        f"📺 لمشاهدة المباراة بدون تقطيع، زوروا موقعنا:\n"
        f"{WEBSITE_URL}\n\n"
        f"📱 تابعونا على تليجرام لتغطية حية للأهداف:\n"
        f"https://t.me/yalla_shoot_today_Group\n\n"
        f"#يلا_شوت #{team_a.replace(' ', '_')} #{team_b.replace(' ', '_')} #مباشر #كرة_القدم"
    )
    url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/feed"
    payload = {"message": fb_text, "access_token": FB_PAGE_TOKEN, "link": WEBSITE_URL}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"[Facebook] Error posting start alert: {e}")

# ─── DELETE OLD MESSAGES ───────────────────────────────────────────────────────
def delete_expired_match_messages():
    """Delete Telegram messages older than 1 day from the channel (best-effort)."""
    if not os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Get message IDs sent >24h ago
    try:
        cursor.execute("""
            SELECT telegram_msg_id FROM match_telegram_msgs
            WHERE sent_at < datetime('now', '-1 day')
            AND deleted = 0
        """)
        rows = cursor.fetchall()
        for (msg_id,) in rows:
            if msg_id:
                res = send_telegram_api("deleteMessage", {"message_id": int(msg_id)})
                if res:
                    cursor.execute(
                        "UPDATE match_telegram_msgs SET deleted = 1 WHERE telegram_msg_id = ?",
                        (msg_id,)
                    )
        conn.commit()
    except Exception as e:
        print(f"[Telegram] Error deleting expired messages: {e}")
    finally:
        conn.close()


def ensure_msg_log_table():
    """Create the message log table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS match_telegram_msgs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT,
            alert_type TEXT,
            telegram_msg_id INTEGER,
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            deleted INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def log_telegram_msg(match_id, alert_type, msg_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO match_telegram_msgs (match_id, alert_type, telegram_msg_id) VALUES (?, ?, ?)",
        (match_id, alert_type, msg_id)
    )
    conn.commit()
    conn.close()


# ─── SCHEDULE FORMAT ──────────────────────────────────────────────────────────
def format_daily_schedule():
    if not os.path.exists(DB_PATH):
        return "لا توجد مباريات مسجلة اليوم."

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT tournament, teamA, teamB, time, status, channel FROM matches")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "📅 لا توجد مباريات مجدولة لليوم."

    # Filter: football only, allowed leagues only
    by_tour = {}
    for tour, team_a, team_b, time_str, status, channel in rows:
        if not is_allowed_match(tour):
            continue
        by_tour.setdefault(tour, []).append((team_a, team_b, time_str, status, channel))

    if not by_tour:
        return "📅 لا توجد مباريات من الدوريات المتاحة اليوم."

    msg = f"📅 <b>جدول مباريات اليوم ({datetime.now().strftime('%Y-%m-%d')})</b>\n\n"
    for tour, matches in by_tour.items():
        msg += f"{get_tournament_emoji(tour)} <b>{tour}</b>:\n"
        for team_a, team_b, time_str, status, channel in matches:
            channel_info = f" | 📺 {channel}" if channel else ""
            status_info = f" ({status})" if status != "لم تبدأ" else ""
            msg += (
                f"  🔹 {get_team_flag(team_a)} {team_a} 🆚 {get_team_flag(team_b)} {team_b}\n"
                f"  ⏰ {time_str}{channel_info}{status_info}\n\n"
            )

    msg += f"🔗 تابع المباريات مباشرة على موقعنا:\n{WEBSITE_URL}"
    return msg


def broadcast_schedule():
    text = format_daily_schedule()
    reply_markup = {
        "inline_keyboard": [
            [{"text": "📺 مشاهدة المباريات بث مباشر", "url": WEBSITE_URL}]
        ]
    }
    msg_id = send_message_and_get_id(text, reply_markup=reply_markup)
    if msg_id:
        try:
            send_telegram_api("unpinAllChatMessages", {})
        except Exception:
            pass
        pin_telegram_message(msg_id)
        return True
    return False


# ─── MATCH ALERTS ─────────────────────────────────────────────────────────────
def check_and_send_alerts():
    if not os.path.exists(DB_PATH):
        return

    ensure_msg_log_table()
    delete_expired_match_messages()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cairo_now = datetime.utcnow() + timedelta(hours=3)
    cairo_today = cairo_now.strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT * FROM matches
        WHERE match_date = ? OR match_date IS NULL
    """, (cairo_today,))
    matches = cursor.fetchall()
    conn.close()

    for m in matches:
        match_id  = m['id']
        team_a    = m['teamA']
        team_b    = m['teamB']
        tournament = m['tournament']
        status    = m['status']
        score_a   = m['scoreA']
        score_b   = m['scoreB']
        time_str  = m['time']

        # ── FILTER: only allowed football leagues ──────────────────────────
        if not is_allowed_match(tournament):
            continue

        keys = m.keys()
        start_sent  = m['telegram_start_sent']  if 'telegram_start_sent'  in keys else 0
        half_sent   = m['telegram_half_sent']   if 'telegram_half_sent'   in keys else 0
        end_sent    = m['telegram_end_sent']    if 'telegram_end_sent'    in keys else 0
        last_score_a = m['last_telegram_scoreA'] if 'last_telegram_scoreA' in keys else None
        last_score_b = m['last_telegram_scoreB'] if 'last_telegram_scoreB' in keys else None

        tour_emoji = get_tournament_emoji(tournament)
        flag_a = get_team_flag(team_a)
        flag_b = get_team_flag(team_b)

        # ── 1. START ALERT ─────────────────────────────────────────────────
        should_send_start = False
        if not start_sent:
            if status in ('جارية الآن',) or 'الشوط' in status:
                should_send_start = True
            elif status == 'لم تبدأ' and time_str and ':' in time_str:
                try:
                    h, mn = map(int, time_str.split(':'))
                    match_dt = cairo_now.replace(hour=h, minute=mn, second=0, microsecond=0)
                    diff = (match_dt - cairo_now).total_seconds()
                    if -900 <= diff <= 900:
                        should_send_start = True
                except Exception:
                    pass

        if should_send_start:
            text = (
                f"🚨 <b>مباراة مرتقبة!</b>\n\n"
                f"{tour_emoji} <b>{tournament}</b>\n"
                f"⚔️ <b>{flag_a} {team_a} 🆚 {flag_b} {team_b}</b>\n\n"
                f"⏰ التوقيت: {time_str} (بتوقيت مصر)\n"
                f"📺 البث المباشر متوفر الآن بجودة عالية!\n"
                f"اضغط زر المشاهدة أدناه 👇"
            )
            reply_markup = {
                "inline_keyboard": [
                    [{"text": "📺 شاهد المباراة بث مباشر الآن", "url": WEBSITE_URL}],
                    [{"text": "🎁 توقع النتيجة واربح 130$", "url": SPONSOR_URL}],
                ]
            }
            msg_id = send_message_and_get_id(text, reply_markup)
            if msg_id:
                log_telegram_msg(match_id, "start", msg_id)
                _update_match(match_id, telegram_start_sent=1)
                # Prediction poll
                try:
                    send_telegram_poll(
                        f"من الفائز: {team_a} VS {team_b}؟",
                        [team_a, "التعادل", team_b]
                    )
                except Exception:
                    pass
                
                # Post to Facebook
                post_fb_start_alert(team_a, team_b, tournament, time_str)
                
                # Start Live Streamer Scoreboard
                try:
                    import subprocess
                    script_path = os.path.join(os.path.dirname(__file__), "live_streamer.py")
                    subprocess.Popen(["python3", script_path, "start", str(match_id), team_a, team_b])
                except Exception as e:
                    print(f"Error starting live stream: {e}")

        # ── 2. GOAL ALERT ──────────────────────────────────────────────────
        is_live = (status == 'جارية الآن' or 'الشوط' in status)
        if is_live and last_score_a is not None and last_score_b is not None:
            try:
                curr_a = int(score_a) if score_a and str(score_a).isdigit() else 0
                curr_b = int(score_b) if score_b and str(score_b).isdigit() else 0
                prev_a = int(last_score_a) if str(last_score_a).isdigit() else 0
                prev_b = int(last_score_b) if str(last_score_b).isdigit() else 0

                if curr_a > prev_a or curr_b > prev_b:
                    scorer_team = team_a if curr_a > prev_a else team_b
                    scorer_flag = flag_a if curr_a > prev_a else flag_b
                    # Try to get scorer name from scraper data
                    scorer_name = _get_scorer_name(match_id, curr_a > prev_a)

                    goal_line = (
                        f"⚽ <b>{scorer_flag} {scorer_team}</b>"
                        + (f" — {scorer_name}" if scorer_name else "")
                    )
                    text = (
                        f"⚽️ <b>جووووول!</b>\n\n"
                        f"{tour_emoji} <b>{tournament}</b>\n"
                        f"⚔️ <b>{flag_a} {team_a} {score_a} - {score_b} {team_b} {flag_b}</b>\n\n"
                        f"{goal_line}\n\n"
                        f"📺 تابع الهدف ومجريات البث المباشر 👇"
                    )
                    reply_markup = {
                        "inline_keyboard": [
                            [{"text": "📺 شاهد الهدف والبث المباشر", "url": WEBSITE_URL}],
                            [{"text": "🎁 توقع النتيجة واربح 130$", "url": SPONSOR_URL}],
                        ]
                    }
                    msg_id = send_message_and_get_id(text, reply_markup)
                    if msg_id:
                        log_telegram_msg(match_id, "goal", msg_id)
            except Exception as e:
                print(f"[Telegram] Goal alert error: {e}")

        # Update score for next comparison
        if is_live:
            _update_match(match_id, last_telegram_scoreA=score_a, last_telegram_scoreB=score_b)
            # Update local score file for FFmpeg to read
            score_file = os.path.join(os.path.dirname(__file__), f"live_score_{match_id}.txt")
            try:
                with open(score_file, "w", encoding="utf-8") as f:
                    f.write(f"{team_a} {score_a} - {score_b} {team_b}")
            except Exception:
                pass

        # ── 3. HALFTIME ALERT ──────────────────────────────────────────────
        is_half = ('بين الشوطين' in status)
        if is_half and not half_sent:
            text = (
                f"⏸️ <b>نهاية الشوط الأول</b>\n\n"
                f"{tour_emoji} <b>{tournament}</b>\n"
                f"⚔️ <b>{flag_a} {team_a} {score_a} 🆚 {score_b} {team_b} {flag_b}</b>\n\n"
                f"📺 لمتابعة الشوط الثاني 👇"
            )
            reply_markup = {
                "inline_keyboard": [
                    [{"text": "📺 تابع البث المباشر الآن", "url": WEBSITE_URL}],
                    [{"text": "🎁 توقع النتيجة واربح 130$", "url": SPONSOR_URL}],
                ]
            }
            msg_id = send_message_and_get_id(text, reply_markup)
            if msg_id:
                log_telegram_msg(match_id, "half", msg_id)
                _update_match(match_id, telegram_half_sent=1)

        # ── 4. END ALERT ───────────────────────────────────────────────────
        is_ended = ('انتهت' in status)
        if is_ended and not end_sent:
            text = (
                f"🏁 <b>نهاية المباراة!</b>\n\n"
                f"{tour_emoji} <b>{tournament}</b>\n"
                f"⚔️ <b>{flag_a} {team_a} {score_a} 🆚 {score_b} {team_b} {flag_b}</b>\n\n"
                f"🎬 شاهد أهداف وملخص المباراة على موقعنا 👇"
            )
            reply_markup = {
                "inline_keyboard": [
                    [{"text": "🎬 شاهد الأهداف والملخص", "url": WEBSITE_URL}],
                    [{"text": "🎁 توقع النتيجة واربح 130$", "url": SPONSOR_URL}],
                ]
            }
            msg_id = send_message_and_get_id(text, reply_markup)
            if msg_id:
                log_telegram_msg(match_id, "end", msg_id)
                _update_match(match_id, telegram_end_sent=1)
                
                # Stop Live Streamer Scoreboard
                try:
                    import subprocess
                    script_path = os.path.join(os.path.dirname(__file__), "live_streamer.py")
                    subprocess.Popen(["python3", script_path, "stop", str(match_id)])
                except Exception as e:
                    print(f"Error stopping live stream: {e}")


# ─── HELPERS ──────────────────────────────────────────────────────────────────
def _update_match(match_id, **fields):
    if not fields:
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cols = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [match_id]
    cursor.execute(f"UPDATE matches SET {cols} WHERE id = ?", vals)
    conn.commit()
    conn.close()


def _get_scorer_name(match_id: str, home_scored: bool) -> str:
    """Scrape Yallakora match center link to find the latest goal scorer name."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT link FROM matches WHERE id = ?", (match_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row or not row[0]:
            return ""
            
        match_link = row[0]
        if not match_link.startswith("http"):
            match_link = f"https://www.yallakora.com{match_link}"
            
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        import urllib.request
        from bs4 import BeautifulSoup
        req = urllib.request.Request(match_link, headers=headers)
        html = urllib.request.urlopen(req, timeout=10).read()
        soup = BeautifulSoup(html, 'html.parser')
        
        # Yallakora goal events are usually in event lists
        # We try to find the latest goal event.
        events = soup.find_all('div', class_='eventItem')
        scorers = []
        for event in events:
            # check if it has goal icon
            icon = event.find('i', class_='icon-goal')
            if icon:
                player_tag = event.find('div', class_='playerName') or event.find('p')
                if player_tag:
                    scorers.append(player_tag.text.strip())
                    
        if scorers:
            # Assuming events might be ordered ascending or descending. We take the last found or first.
            # Yallakora timeline is usually top-down (latest at top). Let's take the first one.
            return scorers[0]
            
    except Exception as e:
        print(f"[Scraper] Error getting scorer name: {e}")
        
    return ""


if __name__ == "__main__":
    print(format_daily_schedule())
