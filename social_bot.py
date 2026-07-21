"""
social_bot.py — نظام النشر التلقائي على فيسبوك وتليجرام
يُشغَّل تلقائياً عبر GitHub Actions كل ساعة
"""
import os
import sqlite3
import requests
import json
import logging
from datetime import datetime, timedelta
from io import BytesIO

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ─── الإعدادات ────────────────────────────────────────────────────────────────
FB_PAGE_TOKEN  = os.getenv("FB_PAGE_TOKEN",  "EAAdEH4WU7sABSJSz3NNu6BuBKUCZCEuuYJHhvcYZCOZAxuJmgUzVHnOnXnESPC1zgCS0tZBih7r0cpWM0zo16TcmULopuyzislyF4sXEBZCwd4vcSbQHZCWA2MtENGRhjPhc2sK3RTKZCosIa4fi5kep77NsmNk2ZBZBXAVfNsa2UknjmO7toUbFYexAyT5WHQLlnXtl7asLA")
FB_PAGE_ID     = os.getenv("FB_PAGE_ID",     "1183659124839160")
TG_BOT_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHANNEL_ID  = os.getenv("TELEGRAM_CHANNEL_ID", "@yalla_shoot_today_Group")
WEBSITE_URL    = os.getenv("WEBSITE_URL",    "https://yalla-shoot-today.vercel.app")
DB_PATH        = os.path.join(os.path.dirname(__file__), "matches.db")
FONT_PATH      = "Cairo-Bold.ttf"
FONT_URL       = "https://github.com/google/fonts/raw/main/ofl/cairo/Cairo-Bold.ttf"

EMOJIS = {
    "دوري أبطال أوروبا": "🏆", "الدوري الإنجليزي": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "الدوري الإسباني": "🇪🇸", "الدوري الإيطالي": "🇮🇹",
    "الدوري الألماني": "🇩🇪", "الدوري الفرنسي": "🇫🇷",
    "الدوري السعودي": "🇸🇦", "الدوري المصري": "🇪🇬",
    "كأس العالم": "🌍", "الدوري الأوروبي": "🇪🇺",
}


# ─── مساعدات ─────────────────────────────────────────────────────────────────
def get_tour_emoji(tour: str) -> str:
    for k, v in EMOJIS.items():
        if k in (tour or ""):
            return v
    return "⚽"


def download_font():
    if not os.path.exists(FONT_PATH):
        logger.info("Downloading Cairo font...")
        r = requests.get(FONT_URL, timeout=30)
        with open(FONT_PATH, "wb") as f:
            f.write(r.content)


def get_logo(url: str, size=(200, 200)):
    """Download team logo, return PIL Image or None."""
    try:
        from PIL import Image
        r = requests.get(url, timeout=10)
        logo = Image.open(BytesIO(r.content)).convert("RGBA")
        logo = logo.resize(size, Image.LANCZOS)
        return logo
    except Exception:
        return None


def render_arabic(text: str) -> str:
    """Reshape Arabic text for Pillow."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


# ─── توليد الصورة ─────────────────────────────────────────────────────────────
def create_match_image(match: dict, label: str = "مباشر") -> str | None:
    """Generate a professional match poster. Returns local file path."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        download_font()

        W, H = 1200, 630
        img = Image.new("RGB", (W, H), "#0f1420")
        draw = ImageDraw.Draw(img)

        # ── Gradient-like overlay strips ──────────────────────────────────
        for y in range(H):
            alpha = int(30 * (1 - y / H))
            r, g, b = 16 + alpha, 20 + alpha // 2, 32 + alpha
            draw.line([(0, y), (W, y)], fill=(r, g, b))

        # ── Fonts ─────────────────────────────────────────────────────────
        f_huge   = ImageFont.truetype(FONT_PATH, 80)
        f_large  = ImageFont.truetype(FONT_PATH, 48)
        f_medium = ImageFont.truetype(FONT_PATH, 36)
        f_small  = ImageFont.truetype(FONT_PATH, 26)

        # ── Tournament banner ─────────────────────────────────────────────
        tour = match.get("tournament", "بطولة كروية")
        tour_rendered = render_arabic(f"{get_tour_emoji(tour)}  {tour}")
        draw.rectangle([(0, 0), (W, 90)], fill="#10b981")
        draw.text((W // 2, 45), tour_rendered, font=f_medium, fill="#ffffff", anchor="mm")

        # ── Team logos ────────────────────────────────────────────────────
        logo_a = get_logo(match.get("logoA", ""), (220, 220))
        logo_b = get_logo(match.get("logoB", ""), (220, 220))

        if logo_a:
            img.paste(logo_a, (W - 310 - 220, H // 2 - 100), logo_a)
        if logo_b:
            img.paste(logo_b, (310, H // 2 - 100), logo_b)

        # ── Team names ────────────────────────────────────────────────────
        name_a = render_arabic(match.get("teamA", "الفريق الأول"))
        name_b = render_arabic(match.get("teamB", "الفريق الثاني"))
        draw.text((W - 420, H // 2 + 145), name_a, font=f_large, fill="#f9fafb", anchor="mm")
        draw.text((420, H // 2 + 145),     name_b, font=f_large, fill="#f9fafb", anchor="mm")

        # ── VS badge ──────────────────────────────────────────────────────
        draw.ellipse([(W // 2 - 70, H // 2 - 50), (W // 2 + 70, H // 2 + 50)], fill="#f43f5e")
        draw.text((W // 2, H // 2), "VS", font=f_huge, fill="#ffffff", anchor="mm")

        # ── Match time ────────────────────────────────────────────────────
        time_str = match.get("time", "")
        if time_str:
            time_rendered = render_arabic(f"⏰  {time_str}  بتوقيت مكة المكرمة")
            draw.text((W // 2, H - 90), time_rendered, font=f_small, fill="#9ca3af", anchor="mm")

        # ── LIVE badge ────────────────────────────────────────────────────
        label_txt = render_arabic(label)
        draw.rounded_rectangle([(W // 2 - 120, H - 160), (W // 2 + 120, H - 110)],
                                radius=20, fill="#ef4444")
        draw.text((W // 2, H - 135), label_txt, font=f_medium, fill="#fff", anchor="mm")

        # ── Website watermark ─────────────────────────────────────────────
        site_txt = render_arabic("yalla-shoot-today.vercel.app")
        draw.text((W // 2, H - 30), site_txt, font=f_small, fill="#4b5563", anchor="mm")

        path = f"post_{match.get('id', 'match')}.png"
        img.save(path, quality=95)
        return path

    except Exception as e:
        logger.error(f"create_match_image error: {e}")
        return None


# ─── فيسبوك ──────────────────────────────────────────────────────────────────
def post_fb_photo(message: str, image_path: str) -> bool:
    """Post an image with caption to Facebook page."""
    if not FB_PAGE_TOKEN or not FB_PAGE_ID:
        logger.warning("Facebook credentials missing.")
        return False
    try:
        url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
        with open(image_path, "rb") as f:
            r = requests.post(url, data={"message": message, "access_token": FB_PAGE_TOKEN}, files={"source": f}, timeout=30)
        logger.info(f"FB photo post: {r.status_code} — {r.text[:120]}")
        return r.status_code == 200
    except Exception as e:
        logger.error(f"post_fb_photo error: {e}")
        return False


def post_fb_link(message: str, link: str) -> bool:
    """Post a link post (text + URL) to Facebook page."""
    if not FB_PAGE_TOKEN or not FB_PAGE_ID:
        return False
    try:
        url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
        r = requests.post(url, json={"message": message, "link": link, "access_token": FB_PAGE_TOKEN}, timeout=30)
        logger.info(f"FB link post: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        logger.error(f"post_fb_link error: {e}")
        return False


# ─── تليجرام ─────────────────────────────────────────────────────────────────
def tg_send_photo(caption: str, image_path: str, btn_text: str = None, btn_url: str = None) -> bool:
    if not TG_BOT_TOKEN or not TG_CHANNEL_ID:
        logger.warning("Telegram credentials missing.")
        return False
    try:
        api_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto"
        payload = {"chat_id": TG_CHANNEL_ID, "caption": caption, "parse_mode": "HTML"}
        if btn_text and btn_url:
            payload["reply_markup"] = json.dumps({
                "inline_keyboard": [[{"text": btn_text, "url": btn_url}]]
            })
        with open(image_path, "rb") as f:
            r = requests.post(api_url, data=payload, files={"photo": f}, timeout=30)
        logger.info(f"TG photo: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        logger.error(f"tg_send_photo error: {e}")
        return False


def tg_send_message(text: str, btn_text: str = None, btn_url: str = None) -> bool:
    if not TG_BOT_TOKEN or not TG_CHANNEL_ID:
        return False
    try:
        api_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHANNEL_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
        if btn_text and btn_url:
            payload["reply_markup"] = json.dumps({
                "inline_keyboard": [[{"text": btn_text, "url": btn_url}]]
            })
        r = requests.post(api_url, json=payload, timeout=20)
        logger.info(f"TG message: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        logger.error(f"tg_send_message error: {e}")
        return False


# ─── قاعدة البيانات ───────────────────────────────────────────────────────────
def get_today_matches() -> list[dict]:
    if not os.path.exists(DB_PATH):
        logger.error(f"DB not found at {DB_PATH}")
        return []
    today = datetime.utcnow() + timedelta(hours=3)  # Cairo time
    today_str = today.strftime("%m/%d")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT id, teamA, teamB, logoA, logoB, time, tournament, date, status
        FROM matches WHERE date = ?
        ORDER BY time ASC
    """, (today_str,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def was_alert_sent(match_id: str, alert_type: str) -> bool:
    """Check DB if this alert was already sent today."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS social_alerts_sent (
                match_id TEXT, alert_type TEXT, sent_at TEXT,
                PRIMARY KEY (match_id, alert_type)
            )
        """)
        conn.commit()
        today = (datetime.utcnow() + timedelta(hours=3)).strftime("%Y-%m-%d")
        cur.execute("SELECT 1 FROM social_alerts_sent WHERE match_id=? AND alert_type=? AND sent_at LIKE ?",
                    (match_id, alert_type, f"{today}%"))
        found = cur.fetchone() is not None
        conn.close()
        return found
    except Exception:
        return False


def mark_alert_sent(match_id: str, alert_type: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        now = (datetime.utcnow() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")
        cur.execute("INSERT OR REPLACE INTO social_alerts_sent VALUES (?, ?, ?)", (match_id, alert_type, now))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"mark_alert_sent error: {e}")


# ─── المهام ──────────────────────────────────────────────────────────────────
def task_daily_schedule():
    """Run once in the morning: post today's schedule with match list."""
    logger.info("=== task_daily_schedule ===")
    matches = get_today_matches()
    if not matches:
        logger.info("No matches today.")
        return

    # Build text
    now_cairo = datetime.utcnow() + timedelta(hours=3)
    day_str = now_cairo.strftime("%d / %m / %Y")
    lines = [f"📅 <b>جدول مباريات اليوم — {day_str}</b>\n"]
    for m in matches:
        emoji = get_tour_emoji(m.get("tournament", ""))
        lines.append(f"{emoji} <b>{m.get('tournament','')}</b>")
        lines.append(f"  ⚽ {m.get('teamA','')} 🆚 {m.get('teamB','')}")
        lines.append(f"  ⏰ {m.get('time','')} بتوقيت مكة المكرمة\n")
    lines.append(f"\n🔴 مشاهدة مباشرة بجودة عالية وبدون تقطيع:\n{WEBSITE_URL}")
    text = "\n".join(lines)

    # Build image from FIRST match
    first = matches[0]
    img_path = create_match_image(first, label="جدول اليوم")

    # Post
    if img_path:
        tg_send_photo(text, img_path, "📺 شاهد الآن", WEBSITE_URL)
        post_fb_photo(text.replace("<b>", "").replace("</b>", ""), img_path)
        os.remove(img_path)
    else:
        tg_send_message(text, "📺 شاهد الآن", WEBSITE_URL)
        post_fb_link(text.replace("<b>", "").replace("</b>", ""), WEBSITE_URL)


def task_match_alerts():
    """Run hourly: check for matches starting in ~60 min."""
    logger.info("=== task_match_alerts ===")
    matches = get_today_matches()
    now_cairo = datetime.utcnow() + timedelta(hours=3)

    for m in matches:
        if m.get("status") == "انتهت":
            continue

        # Parse match time
        try:
            hour, minute = map(int, m.get("time", "00:00").split(":"))
            match_dt = now_cairo.replace(hour=hour, minute=minute, second=0, microsecond=0)
        except Exception:
            continue

        diff_min = (match_dt - now_cairo).total_seconds() / 60

        # Alert 60 minutes before
        if 50 <= diff_min <= 70 and not was_alert_sent(m["id"], "pre60"):
            logger.info(f"Sending 60-min alert for {m['teamA']} vs {m['teamB']}")
            text = (
                f"⏳ <b>ساعة واحدة تفصلنا!</b>\n\n"
                f"⚽ <b>{m['teamA']}</b> 🆚 <b>{m['teamB']}</b>\n"
                f"🏆 {m.get('tournament','')}\n"
                f"⏰ {m.get('time','')} بتوقيت مكة المكرمة\n\n"
                f"🔥 البث المباشر جاهز — شاهد بدون تقطيع!\n{WEBSITE_URL}/?match={m['id']}"
            )
            img_path = create_match_image(m, label="قريباً")
            link = f"{WEBSITE_URL}/?match={m['id']}"
            if img_path:
                tg_send_photo(text, img_path, "📺 شاهد الآن", link)
                post_fb_photo(text.replace("<b>","").replace("</b>",""), img_path)
                os.remove(img_path)
            else:
                tg_send_message(text, "📺 شاهد الآن", link)
            mark_alert_sent(m["id"], "pre60")

        # Alert 10 minutes before (start soon)
        elif 5 <= diff_min <= 15 and not was_alert_sent(m["id"], "pre10"):
            logger.info(f"Sending 10-min alert for {m['teamA']} vs {m['teamB']}")
            text = (
                f"🚨 <b>المباراة تبدأ بعد دقائق!</b>\n\n"
                f"⚽ <b>{m['teamA']}</b> 🆚 <b>{m['teamB']}</b>\n"
                f"🔴 البث المباشر شغال الآن!\n{WEBSITE_URL}/?match={m['id']}"
            )
            link = f"{WEBSITE_URL}/?match={m['id']}"
            img_path = create_match_image(m, label="🔴 مباشر الآن")
            if img_path:
                tg_send_photo(text, img_path, "🔴 شاهد الآن", link)
                post_fb_photo(text.replace("<b>","").replace("</b>",""), img_path)
                os.remove(img_path)
            else:
                tg_send_message(text, "🔴 شاهد الآن", link)
            mark_alert_sent(m["id"], "pre10")


# ─── الدخول الرئيسي ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "alerts"

    if mode == "schedule":
        task_daily_schedule()
    elif mode == "alerts":
        task_match_alerts()
    else:
        logger.error(f"Unknown mode: {mode}. Use 'schedule' or 'alerts'")
