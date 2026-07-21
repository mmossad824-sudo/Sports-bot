"""
social_bot.py — نظام النشر التلقائي الشامل على فيسبوك وتليجرام
يُشغَّل تلقائياً عبر GitHub Actions كل ساعة
الإصدار 2.0 — يجلب البيانات من Hugging Face API مباشرة (لا يحتاج DB محلية)
"""
import os
import sqlite3
import requests
import json
import logging
import hashlib
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from io import BytesIO

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ─── الإعدادات ────────────────────────────────────────────────────────────────
FB_PAGE_TOKEN  = os.getenv("FB_PAGE_TOKEN",  "")          # يُقرأ من GitHub Secret
FB_PAGE_ID     = os.getenv("FB_PAGE_ID",     "1183659124839160")
TG_BOT_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHANNEL_ID  = os.getenv("TELEGRAM_CHANNEL_ID", "@yalla_shoot_today_Group")
WEBSITE_URL    = os.getenv("WEBSITE_URL",    "https://yalla-shoot-today.vercel.app")
HF_API_URL     = os.getenv("HF_API_URL",     "https://mmossad824-sports-bot.hf.space")
FONT_PATH      = "Cairo-Bold.ttf"
FONT_URL       = "https://fonts.gstatic.com/s/cairo/v31/SLXgc1nY6HkvangtZmpQdkhzfH5lkSs2SgRjCAGMQ1z0hAc5W1Q.ttf"
SPONSOR_URL    = "https://www.profitablecpmrate.com/e4480b4a0a4ef0a7e842009f7c505039"

# State file to avoid duplicate posts
STATE_FILE = "social_bot_state.json"

# ─── RSS Feeds لأخبار كرة القدم ──────────────────────────────────────────────
RSS_FEEDS = [
    {
        "name": "BBC Arabic Sport",
        "url": "https://feeds.bbci.co.uk/arabic/sport/rss.xml",
        "lang": "ar"
    },
    {
        "name": "Sport360 Arabic",
        "url": "https://arabic.sport360.com/feed/",
        "lang": "ar"
    },
    {
        "name": "BBC Sport Football",
        "url": "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "lang": "en"
    },
]

EMOJIS = {
    "دوري أبطال أوروبا": "🏆", "الدوري الإنجليزي": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "الدوري الإسباني": "🇪🇸", "الدوري الإيطالي": "🇮🇹",
    "الدوري الألماني": "🇩🇪", "الدوري الفرنسي": "🇫🇷",
    "الدوري السعودي": "🇸🇦", "الدوري المصري": "🇪🇬",
    "كأس العالم": "🌍🏆", "الدوري الأوروبي": "🇪🇺",
    "premier league": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "champions league": "🏆",
    "la liga": "🇪🇸", "serie a": "🇮🇹",
    "bundesliga": "🇩🇪", "ligue 1": "🇫🇷",
}


# ─── State Management (منع التكرار) ──────────────────────────────────────────
def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"sent_alerts": {}, "sent_news": [], "last_schedule_date": ""}


def save_state(state: dict):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"save_state error: {e}")


def was_sent(state: dict, key: str, match_id: str = "") -> bool:
    full_key = f"{key}_{match_id}" if match_id else key
    return full_key in state.get("sent_alerts", {})


def mark_sent(state: dict, key: str, match_id: str = ""):
    full_key = f"{key}_{match_id}" if match_id else key
    if "sent_alerts" not in state:
        state["sent_alerts"] = {}
    state["sent_alerts"][full_key] = datetime.utcnow().isoformat()
    # Clean old entries (> 2 days)
    two_days_ago = (datetime.utcnow() - timedelta(days=2)).isoformat()
    state["sent_alerts"] = {
        k: v for k, v in state["sent_alerts"].items() if v > two_days_ago
    }


# ─── مساعدات ─────────────────────────────────────────────────────────────────
def get_tour_emoji(tour: str) -> str:
    tour_lower = (tour or "").lower()
    for k, v in EMOJIS.items():
        if k.lower() in tour_lower:
            return v
    return "⚽"


def download_font():
    if not os.path.exists(FONT_PATH):
        logger.info("Downloading Cairo font...")
        try:
            r = requests.get(FONT_URL, timeout=30)
            r.raise_for_status()
            with open(FONT_PATH, "wb") as f:
                f.write(r.content)
            logger.info("Font downloaded successfully.")
        except Exception as e:
            logger.error(f"Font download failed: {e}")


# Direct PNG logos mapping for top clubs & teams as fallback
TEAM_LOGOS_FALLBACK = {
    "ريال مدريد": "https://media.api-sports.io/football/teams/541.png",
    "برشلونة": "https://media.api-sports.io/football/teams/529.png",
    "ليفربول": "https://media.api-sports.io/football/teams/40.png",
    "مانشستر سيتي": "https://media.api-sports.io/football/teams/50.png",
    "مانشستر يونايتد": "https://media.api-sports.io/football/teams/33.png",
    "أرسنال": "https://media.api-sports.io/football/teams/42.png",
    "تشيلسي": "https://media.api-sports.io/football/teams/49.png",
    "بايرن ميونخ": "https://media.api-sports.io/football/teams/157.png",
    "باريس سان جيرمان": "https://media.api-sports.io/football/teams/85.png",
    "يوفنتوس": "https://media.api-sports.io/football/teams/496.png",
    "إنتر ميلان": "https://media.api-sports.io/football/teams/505.png",
    "إي سي ميلان": "https://media.api-sports.io/football/teams/489.png",
    "الهلال": "https://media.api-sports.io/football/teams/2939.png",
    "النصر": "https://media.api-sports.io/football/teams/2934.png",
    "الاتحاد": "https://media.api-sports.io/football/teams/2932.png",
    "الأهلي": "https://media.api-sports.io/football/teams/1027.png",
    "الزمالك": "https://media.api-sports.io/football/teams/1028.png",
    "بيراميدز": "https://media.api-sports.io/football/teams/3034.png",
}


def get_logo(url: str, team_name: str = "", size=(200, 200)):
    """Download team logo, return PIL Image or None with automatic fallback support."""
    urls_to_try = []
    if url and url.startswith("http") and not url.endswith(".svg"):
        urls_to_try.append(url)

    # Check fallback map
    for team_key, fallback_url in TEAM_LOGOS_FALLBACK.items():
        if team_key in team_name:
            urls_to_try.append(fallback_url)
            break

    from PIL import Image
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    for logo_url in urls_to_try:
        try:
            r = requests.get(logo_url, headers=headers, timeout=10)
            if r.status_code == 200:
                logo = Image.open(BytesIO(r.content)).convert("RGBA")
                logo = logo.resize(size, Image.LANCZOS)
                return logo
        except Exception:
            continue

    return None


def render_arabic(text: str) -> str:
    """Reshape Arabic text for Pillow correctly line by line."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        lines = text.split("\n")
        reshaped_lines = []
        for line in lines:
            reshaped = arabic_reshaper.reshape(line)
            bidi_line = get_display(reshaped)
            reshaped_lines.append(bidi_line)
        return "\n".join(reshaped_lines)
    except Exception:
        return text


# ─── توليد الصورة الاحترافية ──────────────────────────────────────────────────
def create_match_image(match: dict, label: str = "مباشر", size: str = "fb") -> str | None:
    """
    Generate a professional match poster.
    size: 'fb' = 1200x630 (Facebook), 'sq' = 1080x1080 (Instagram/Stories)
    Returns local file path or None.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        download_font()
        if not os.path.exists(FONT_PATH):
            return None

        W, H = (1200, 630) if size == "fb" else (1080, 1080)
        img = Image.new("RGB", (W, H), "#0d1117")
        draw = ImageDraw.Draw(img)

        # ── Background gradient ───────────────────────────────────────────────
        for y in range(H):
            ratio = y / H
            r = int(13 + ratio * 10)
            g = int(17 + ratio * 5)
            b = int(23 + ratio * 20)
            draw.line([(0, y), (W, y)], fill=(r, g, b))

        # ── Decorative circles (background art) ───────────────────────────────
        draw.ellipse([(W - 300, -100), (W + 100, 300)], fill=(16, 185, 129, 30))
        draw.ellipse([(-100, H - 200), (200, H + 100)], fill=(244, 63, 94, 20))

        # ── Fonts ─────────────────────────────────────────────────────────────
        f_huge   = ImageFont.truetype(FONT_PATH, 90 if size == "fb" else 80)
        f_large  = ImageFont.truetype(FONT_PATH, 52 if size == "fb" else 48)
        f_medium = ImageFont.truetype(FONT_PATH, 38 if size == "fb" else 34)
        f_small  = ImageFont.truetype(FONT_PATH, 26 if size == "fb" else 24)

        # ── Tournament banner ─────────────────────────────────────────────────
        tour = match.get("tournament", "Football")
        tour_txt = f"{get_tour_emoji(tour)}  {tour}"
        # Gradient banner
        for y in range(100):
            clr = (16, 185, 129)
            draw.line([(0, y), (W, y)], fill=clr)
        draw.text((W // 2, 50), tour_txt, font=f_medium, fill="#ffffff", anchor="mm", direction="rtl", language="ar")

        # ── Center divider line ───────────────────────────────────────────────
        mid_y = H // 2
        draw.line([(W//2 - 2, 120), (W//2 - 2, H - 120)], fill="#374151", width=2)

        # ── Team logos ────────────────────────────────────────────────────────
        logo_size = (200, 200) if size == "fb" else (180, 180)
        logo_a = get_logo(match.get("logoA", ""), team_name=match.get("teamA", ""), size=logo_size)
        logo_b = get_logo(match.get("logoB", ""), team_name=match.get("teamB", ""), size=logo_size)

        logo_a_x = W // 4 - logo_size[0] // 2
        logo_b_x = 3 * W // 4 - logo_size[1] // 2
        logo_y = mid_y - logo_size[1] // 2 - 20

        if logo_a:
            img.paste(logo_a, (logo_a_x, logo_y), logo_a)
        else:
            draw.ellipse([(logo_a_x, logo_y), (logo_a_x + logo_size[0], logo_y + logo_size[1])],
                         outline="#10b981", width=3)
            draw.text((logo_a_x + logo_size[0]//2, logo_y + logo_size[1]//2),
                      "⚽", font=f_large, anchor="mm")

        if logo_b:
            img.paste(logo_b, (logo_b_x, logo_y), logo_b)
        else:
            draw.ellipse([(logo_b_x, logo_y), (logo_b_x + logo_size[0], logo_y + logo_size[1])],
                         outline="#f43f5e", width=3)
            draw.text((logo_b_x + logo_size[0]//2, logo_y + logo_size[1]//2),
                      "⚽", font=f_large, anchor="mm")

        # ── Team names ────────────────────────────────────────────────────────
        name_a = match.get("teamA", "Team A")
        name_b = match.get("teamB", "Team B")
        name_y = logo_y + logo_size[1] + 30
        draw.text((W // 4, name_y), name_a, font=f_large, fill="#f9fafb", anchor="mm", direction="rtl", language="ar")
        draw.text((3 * W // 4, name_y), name_b, font=f_large, fill="#f9fafb", anchor="mm", direction="rtl", language="ar")

        # ── VS badge ──────────────────────────────────────────────────────────
        vs_r = 65
        vs_cx, vs_cy = W // 2, mid_y - 10
        for offset in range(8, 0, -1):
            draw.ellipse([
                (vs_cx - vs_r - offset, vs_cy - vs_r - offset),
                (vs_cx + vs_r + offset, vs_cy + vs_r + offset)
            ], fill=(244, 63, 94))
        draw.ellipse([(vs_cx - vs_r, vs_cy - vs_r), (vs_cx + vs_r, vs_cy + vs_r)], fill="#f43f5e")
        draw.text((vs_cx, vs_cy), "VS", font=f_huge, fill="#ffffff", anchor="mm")

        # ── Score (if match is live/finished) ─────────────────────────────────
        score_a = match.get("scoreA", "")
        score_b = match.get("scoreB", "")
        status  = match.get("status", "")
        if score_a and score_b and status not in ("لم تبدأ", ""):
            score_text = f"{score_a}  —  {score_b}"
            draw.text((W // 2, name_y + 50), score_text, font=f_large, fill="#fbbf24", anchor="mm")

        # ── Match time ────────────────────────────────────────────────────────
        time_str = match.get("time", "")
        if time_str:
            time_txt = f"⏰  {time_str}  بتوقيت القاهرة"
            draw.text((W // 2, H - 85), time_txt, font=f_small, fill="#9ca3af", anchor="mm", direction="rtl", language="ar")

        # ── LIVE / Label badge ────────────────────────────────────────────────
        badge_w = 240
        draw.rounded_rectangle([
            (W // 2 - badge_w // 2, H - 160),
            (W // 2 + badge_w // 2, H - 110)
        ], radius=25, fill="#ef4444" if "مباشر" in label or "LIVE" in label else "#10b981")
        draw.text((W // 2, H - 135), label, font=f_medium, fill="#fff", anchor="mm", direction="rtl", language="ar")

        # ── Website watermark ─────────────────────────────────────────────────
        draw.text((W // 2, H - 28), "yalla-shoot-today.vercel.app", font=f_small, fill="#4b5563", anchor="mm")

        path = f"post_{match.get('id', 'match')}_{size}.png"
        img.save(path, "PNG", optimize=True)
        return path

    except Exception as e:
        logger.error(f"create_match_image error: {e}")
        return None


def create_news_image(title: str, source: str = "") -> str | None:
    """Generate a news card image."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        download_font()
        if not os.path.exists(FONT_PATH):
            return None

        W, H = 1200, 630
        img = Image.new("RGB", (W, H), "#0d1117")
        draw = ImageDraw.Draw(img)

        # Background
        for y in range(H):
            ratio = y / H
            r = int(13 + ratio * 8)
            g = int(17 + ratio * 5)
            b = int(23 + ratio * 15)
            draw.line([(0, y), (W, y)], fill=(r, g, b))

        # Header strip
        for y in range(100):
            draw.line([(0, y), (W, y)], fill=(5, 150, 105))

        f_title  = ImageFont.truetype(FONT_PATH, 54)
        f_medium = ImageFont.truetype(FONT_PATH, 36)
        f_small  = ImageFont.truetype(FONT_PATH, 26)

        # Header
        header = "⚡ خبر عاجل | Breaking News"
        draw.text((W // 2, 50), header, font=f_medium, fill="#ffffff", anchor="mm", direction="rtl", language="ar")

        # News icon
        draw.text((W // 2, H // 2 - 80), "📰", font=ImageFont.truetype(FONT_PATH, 80), anchor="mm")

        # Title — word wrap
        words = title.split()
        lines, line = [], []
        for word in words:
            line.append(word)
            test = " ".join(line)
            bbox = draw.textbbox((0, 0), test, font=f_title)
            if bbox[2] > W - 80:
                lines.append(" ".join(line[:-1]))
                line = [word]
        if line:
            lines.append(" ".join(line))

        y_start = H // 2 + 20
        for i, ln in enumerate(lines[:3]):
            draw.text((W // 2, y_start + i * 65), ln, font=f_title, fill="#f9fafb", anchor="mm", direction="rtl", language="ar")

        # Source
        if source:
            src_txt = f"المصدر: {source}"
            draw.text((W // 2, H - 80), src_txt, font=f_small, fill="#9ca3af", anchor="mm", direction="rtl", language="ar")

        # Watermark
        draw.text((W // 2, H - 28), "yalla-shoot-today.vercel.app", font=f_small, fill="#4b5563", anchor="mm")

        path = f"news_{hashlib.md5(title.encode()).hexdigest()[:8]}.png"
        img.save(path, "PNG", optimize=True)
        return path
    except Exception as e:
        logger.error(f"create_news_image error: {e}")
        return None


# ─── جلب بيانات المباريات من Hugging Face API ────────────────────────────────
def get_today_matches() -> list[dict]:
    """Fetch today's matches from HF API first, fallback to local DB."""
    try:
        logger.info(f"Fetching matches from HF API: {HF_API_URL}")
        r = requests.get(f"{HF_API_URL}/api/matches", timeout=20)
        if r.status_code == 200:
            all_matches = r.json()
            now_cairo = datetime.utcnow() + timedelta(hours=3)
            today_str = now_cairo.strftime("%m/%d")
            today_alt = now_cairo.strftime("%-m/%-d")
            today_alt2 = f"{now_cairo.month}/{now_cairo.day}"  # no leading zeros
            today_dates = {today_str, today_alt, today_alt2}

            # Try to filter by date first
            today_matches = [
                m for m in all_matches
                if m.get("date") in today_dates
                and m.get("status") != "انتهت"
            ]

            if today_matches:
                logger.info(f"Got {len(today_matches)} today matches from HF API")
                return today_matches

            # If matches have empty date or no date filter, return all non-finished
            active_matches = [
                m for m in all_matches
                if m.get("status") not in ("انتهت", "finished")
            ]
            if active_matches:
                logger.info(f"No date filter match — returning {len(active_matches)} active matches")
                return active_matches

            # Last resort: return all
            logger.info(f"Returning all {len(all_matches)} matches (no filter match)")
            return all_matches

    except Exception as e:
        logger.warning(f"HF API failed: {e} — falling back to local DB")

    # Fallback: local SQLite
    db_path = os.path.join(os.path.dirname(__file__), "matches.db")
    if not os.path.exists(db_path):
        logger.error("No local DB found either.")
        return []
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        now_cairo = datetime.utcnow() + timedelta(hours=3)
        today_str = now_cairo.strftime("%m/%d")
        cur.execute("SELECT * FROM matches WHERE date = ? ORDER BY time ASC", (today_str,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Local DB error: {e}")
        return []


def get_all_today_matches_for_schedule() -> list[dict]:
    """Get ALL today matches including finished for morning schedule."""
    try:
        r = requests.get(f"{HF_API_URL}/api/matches", timeout=20)
        if r.status_code == 200:
            all_matches = r.json()
            now_cairo = datetime.utcnow() + timedelta(hours=3)
            today_str = now_cairo.strftime("%m/%d")
            today_alt = now_cairo.strftime("%-m/%-d")
            return [
                m for m in all_matches
                if m.get("date") in (today_str, today_alt)
            ]
    except Exception as e:
        logger.warning(f"get_all_today_matches error: {e}")
    return []


# ─── فيسبوك ──────────────────────────────────────────────────────────────────
def post_fb_photo(message: str, image_path: str) -> bool:
    """Post an image with caption to Facebook page."""
    if not FB_PAGE_TOKEN or not FB_PAGE_ID:
        logger.warning("Facebook credentials missing — set FB_PAGE_TOKEN env var.")
        return False
    try:
        url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
        with open(image_path, "rb") as f:
            r = requests.post(
                url,
                data={"message": message, "access_token": FB_PAGE_TOKEN},
                files={"source": f},
                timeout=30
            )
        data = r.json()
        if r.status_code == 200 and data.get("id"):
            logger.info(f"✅ FB photo posted: id={data.get('id')}")
            return True
        else:
            logger.error(f"FB photo failed: {r.status_code} — {r.text[:300]}")
            return False
    except Exception as e:
        logger.error(f"post_fb_photo error: {e}")
        return False


def post_fb_text(message: str, link: str = "") -> bool:
    """Post a text (+ optional link) post to Facebook page."""
    if not FB_PAGE_TOKEN or not FB_PAGE_ID:
        return False
    try:
        url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
        payload = {"message": message, "access_token": FB_PAGE_TOKEN}
        if link:
            payload["link"] = link
        r = requests.post(url, json=payload, timeout=30)
        data = r.json()
        if r.status_code == 200 and data.get("id"):
            logger.info(f"✅ FB text posted: id={data.get('id')}")
            return True
        else:
            logger.error(f"FB text failed: {r.status_code} — {r.text[:300]}")
            return False
    except Exception as e:
        logger.error(f"post_fb_text error: {e}")
        return False


# ─── تليجرام ─────────────────────────────────────────────────────────────────
def tg_send_photo(caption: str, image_path: str,
                  btn_text: str = None, btn_url: str = None) -> bool:
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
        ok = r.status_code == 200
        if ok:
            logger.info("✅ TG photo sent")
        else:
            logger.error(f"TG photo failed: {r.text[:200]}")
        return ok
    except Exception as e:
        logger.error(f"tg_send_photo error: {e}")
        return False


def tg_send_message(text: str, btn_text: str = None, btn_url: str = None) -> bool:
    if not TG_BOT_TOKEN or not TG_CHANNEL_ID:
        return False
    try:
        api_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TG_CHANNEL_ID, "text": text,
            "parse_mode": "HTML", "disable_web_page_preview": True
        }
        if btn_text and btn_url:
            payload["reply_markup"] = json.dumps({
                "inline_keyboard": [[{"text": btn_text, "url": btn_url}]]
            })
        r = requests.post(api_url, json=payload, timeout=20)
        ok = r.status_code == 200
        if ok:
            logger.info("✅ TG message sent")
        else:
            logger.error(f"TG message failed: {r.text[:200]}")
        return ok
    except Exception as e:
        logger.error(f"tg_send_message error: {e}")
        return False


# ─── نظام الأخبار RSS ────────────────────────────────────────────────────────
def fetch_rss_news(max_per_feed: int = 3) -> list[dict]:
    """Fetch latest football news from RSS feeds."""
    all_items = []
    for feed in RSS_FEEDS:
        try:
            headers = {"User-Agent": "Mozilla/5.0 Sports-Bot/2.0"}
            r = requests.get(feed["url"], headers=headers, timeout=15)
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.content)
            channel = root.find("channel")
            if not channel:
                continue
            items = channel.findall("item")[:max_per_feed]
            for item in items:
                title = (item.findtext("title") or "").strip()
                link  = (item.findtext("link")  or "").strip()
                pub   = (item.findtext("pubDate") or "").strip()
                desc  = (item.findtext("description") or "").strip()[:200]
                if title:
                    all_items.append({
                        "title": title,
                        "link": link,
                        "pub": pub,
                        "desc": desc,
                        "source": feed["name"],
                        "lang": feed["lang"],
                        "id": hashlib.md5(title.encode()).hexdigest()[:12],
                    })
        except Exception as e:
            logger.warning(f"RSS feed error ({feed['name']}): {e}")
    return all_items


def format_news_post(item: dict) -> tuple[str, str]:
    """Returns (fb_text, tg_text) for a news item."""
    title = item["title"]
    source = item["source"]
    link = item["link"]
    lang = item.get("lang", "ar")

    if lang == "ar":
        fb_text = (
            f"📰 {title}\n\n"
            f"🔗 {link}\n\n"
            f"⚽ تابع أحدث أخبار كرة القدم وشاهد المباريات مباشرة:\n"
            f"{WEBSITE_URL}\n\n"
            f"#كرة_القدم #أخبار_كورة #يلا_شوت"
        )
        tg_text = (
            f"📰 <b>{title}</b>\n\n"
            f"📌 المصدر: {source}\n"
            f"🔗 <a href='{link}'>اقرأ المزيد</a>\n\n"
            f"⚽ شاهد المباريات مباشرة:\n{WEBSITE_URL}"
        )
    else:
        fb_text = (
            f"📰 {title}\n\n"
            f"🔗 {link}\n\n"
            f"⚽ Watch live football matches at:\n"
            f"{WEBSITE_URL}\n\n"
            f"#Football #Soccer #LiveStream #YallaShoot"
        )
        tg_text = (
            f"📰 <b>{title}</b>\n\n"
            f"📌 Source: {source}\n"
            f"🔗 <a href='{link}'>Read more</a>\n\n"
            f"⚽ Watch live: {WEBSITE_URL}"
        )
    return fb_text, tg_text


# ─── المهمة 1: الجدول الصباحي ────────────────────────────────────────────────
def task_daily_schedule(state: dict):
    """Run once in the morning: post today's full schedule."""
    logger.info("=== task_daily_schedule ===")

    now_cairo = datetime.utcnow() + timedelta(hours=3)
    today_key = f"schedule_{now_cairo.strftime('%Y-%m-%d')}"
    if was_sent(state, today_key):
        logger.info("Schedule already sent today — skipping.")
        return

    matches = get_all_today_matches_for_schedule()
    if not matches:
        logger.info("No matches today.")
        return

    day_str = now_cairo.strftime("%d / %m / %Y")

    # ── Arabic text ───────────────────────────────────────────────────────────
    lines_ar = [f"📅 جدول مباريات اليوم — {day_str}\n"]
    lines_en = [f"📅 Today's Match Schedule — {day_str}\n"]

    for m in matches[:12]:  # Max 12 matches
        emoji = get_tour_emoji(m.get("tournament", ""))
        tour_ar = m.get("tournament", "")
        team_a  = m.get("teamA", "")
        team_b  = m.get("teamB", "")
        t       = m.get("time", "")

        lines_ar.append(f"{emoji} {tour_ar}")
        lines_ar.append(f"  ⚽ {team_a} 🆚 {team_b}  ⏰ {t}\n")

        lines_en.append(f"{emoji} {tour_ar}")
        lines_en.append(f"  ⚽ {team_a} 🆚 {team_b}  ⏰ {t}\n")

    # AR footer
    lines_ar.append(f"\n🔴 بث مباشر بجودة HD بدون تقطيع:\n{WEBSITE_URL}")
    lines_ar.append(f"📱 اشترك في قناة التليجرام للتنبيهات الفورية!")
    lines_ar.append(f"\n#يلا_شوت #بث_مباشر #مباريات_اليوم #كورة_مباشرة")

    # EN footer
    lines_en.append(f"\n🔴 Watch HD Live Streams:\n{WEBSITE_URL}")
    lines_en.append(f"#Football #LiveStream #Soccer #YallaShoot #LiveFootball")

    text_ar = "\n".join(lines_ar)
    text_en = "\n".join(lines_en)
    full_fb_text = text_ar + "\n\n" + "─" * 30 + "\n\n" + text_en
    tg_text = "\n".join([
        f"📅 <b>جدول مباريات اليوم — {day_str}</b>\n"
    ] + [
        f"{get_tour_emoji(m.get('tournament',''))} <b>{m.get('tournament','')}</b>\n"
        f"  ⚽ {m.get('teamA','')} 🆚 {m.get('teamB','')}  ⏰ {m.get('time','')}\n"
        for m in matches[:10]
    ] + [f"\n🔴 <a href='{WEBSITE_URL}'>مشاهدة مباشرة بجودة HD</a>"])

    # Build image from first match
    first = matches[0]
    img_path = create_match_image(first, label="جدول اليوم | Today's Schedule")

    # Post to both platforms
    if img_path:
        tg_send_photo(tg_text, img_path, "📺 شاهد الآن", WEBSITE_URL)
        post_fb_photo(full_fb_text, img_path)
        try:
            os.remove(img_path)
        except Exception:
            pass
    else:
        tg_send_message(tg_text, "📺 شاهد الآن", WEBSITE_URL)
        post_fb_text(full_fb_text, WEBSITE_URL)

    mark_sent(state, today_key)
    logger.info("✅ Daily schedule posted!")


# ─── المهمة 2: تنبيهات المباريات القادمة ─────────────────────────────────────
def task_match_alerts(state: dict):
    """Run hourly: post alerts for upcoming matches."""
    logger.info("=== task_match_alerts ===")
    matches = get_today_matches()
    now_cairo = datetime.utcnow() + timedelta(hours=3)

    for m in matches:
        match_id = m.get("id", "")
        team_a   = m.get("teamA", "")
        team_b   = m.get("teamB", "")
        tour     = m.get("tournament", "")
        status   = m.get("status", "")

        if status in ("انتهت", "finished"):
            continue

        try:
            hour, minute = map(int, m.get("time", "00:00").split(":"))
            match_dt = now_cairo.replace(hour=hour, minute=minute, second=0, microsecond=0)
        except Exception:
            continue

        diff_min = (match_dt - now_cairo).total_seconds() / 60

        # ── Alert 60 minutes before ───────────────────────────────────────────
        if 50 <= diff_min <= 70 and not was_sent(state, "pre60", match_id):
            logger.info(f"60-min alert: {team_a} vs {team_b}")
            link = f"{WEBSITE_URL}/?match={match_id}"

            # Arabic + English
            fb_text = (
                f"⏳ ساعة واحدة تفصلنا!\n\n"
                f"⚽ {team_a} 🆚 {team_b}\n"
                f"🏆 {tour}\n"
                f"⏰ {m.get('time','')} (القاهرة / Cairo)\n\n"
                f"🔥 البث المباشر جاهز — شاهد بجودة HD:\n{link}\n\n"
                f"One hour to go! Live stream ready! 🔴\n\n"
                f"#يلا_شوت #بث_مباشر #{team_a.replace(' ','_')} #{team_b.replace(' ','_')}"
            )
            tg_text = (
                f"⏳ <b>ساعة واحدة تفصلنا!</b>\n\n"
                f"⚽ <b>{team_a}</b> 🆚 <b>{team_b}</b>\n"
                f"🏆 {tour}\n"
                f"⏰ {m.get('time','')} بتوقيت القاهرة\n\n"
                f"🔥 البث المباشر جاهز الآن!\n{link}"
            )
            img_path = create_match_image(m, label="⏳ قريباً | Coming Soon")
            if img_path:
                tg_send_photo(tg_text, img_path, "📺 شاهد الآن", link)
                post_fb_photo(fb_text, img_path)
                try:
                    os.remove(img_path)
                except Exception:
                    pass
            else:
                tg_send_message(tg_text, "📺 شاهد الآن", link)
                post_fb_text(fb_text, link)
            mark_sent(state, "pre60", match_id)

        # ── Alert 10 minutes before ───────────────────────────────────────────
        elif 5 <= diff_min <= 15 and not was_sent(state, "pre10", match_id):
            logger.info(f"10-min alert: {team_a} vs {team_b}")
            link = f"{WEBSITE_URL}/?match={match_id}"

            fb_text = (
                f"🚨 المباراة تبدأ بعد دقائق!\n\n"
                f"⚽ {team_a} 🆚 {team_b}\n"
                f"🏆 {tour}\n"
                f"🔴 البث المباشر شغال الآن!\n{link}\n\n"
                f"🚨 Match starts in minutes! Stream is LIVE!\n\n"
                f"#مباشر #LiveNow #Football"
            )
            tg_text = (
                f"🚨 <b>المباراة تبدأ بعد دقائق!</b>\n\n"
                f"⚽ <b>{team_a}</b> 🆚 <b>{team_b}</b>\n"
                f"🔴 البث المباشر شغال الآن!\n{link}"
            )
            img_path = create_match_image(m, label="🔴 مباشر الآن | LIVE NOW")
            if img_path:
                tg_send_photo(tg_text, img_path, "🔴 شاهد الآن", link)
                post_fb_photo(fb_text, img_path)
                try:
                    os.remove(img_path)
                except Exception:
                    pass
            else:
                tg_send_message(tg_text, "🔴 شاهد الآن", link)
                post_fb_text(fb_text, link)
            mark_sent(state, "pre10", match_id)

        # ── Alert when match starts (live now) ────────────────────────────────
        elif -5 <= diff_min <= 10 and not was_sent(state, "live", match_id):
            if status in ("جارية الآن",) or "الشوط" in status:
                logger.info(f"LIVE alert: {team_a} vs {team_b}")
                link = f"{WEBSITE_URL}/?match={match_id}"

                fb_text = (
                    f"🔴 انطلقت المباراة الآن!\n\n"
                    f"⚽ {team_a} 🆚 {team_b}\n"
                    f"🏆 {tour}\n"
                    f"📺 شاهد البث المباشر الآن:\n{link}\n\n"
                    f"🔴 LIVE NOW! Don't miss it!\n\n"
                    f"#مباشر #LIVE #Football #يلا_شوت"
                )
                tg_text = (
                    f"🔴 <b>المباراة انطلقت الآن!</b>\n\n"
                    f"⚽ <b>{team_a}</b> 🆚 <b>{team_b}</b>\n"
                    f"📺 <a href='{link}'>شاهد البث المباشر</a>"
                )
                img_path = create_match_image(m, label="🔴 LIVE NOW | مباشر الآن")
                if img_path:
                    tg_send_photo(tg_text, img_path, "🔴 مباشر الآن", link)
                    post_fb_photo(fb_text, img_path)
                    try:
                        os.remove(img_path)
                    except Exception:
                        pass
                else:
                    tg_send_message(tg_text, "🔴 مباشر الآن", link)
                    post_fb_text(fb_text, link)
                mark_sent(state, "live", match_id)


# ─── المهمة 3: أخبار RSS ─────────────────────────────────────────────────────
def task_post_news(state: dict, max_news: int = 2):
    """Fetch and post latest football news."""
    logger.info("=== task_post_news ===")
    items = fetch_rss_news(max_per_feed=2)

    sent_count = 0
    for item in items:
        if sent_count >= max_news:
            break
        news_id = item["id"]
        if news_id in state.get("sent_news", []):
            continue

        fb_text, tg_text = format_news_post(item)

        # Try to create news image
        img_path = create_news_image(item["title"], item["source"])

        tg_ok  = False
        fb_ok  = False

        if img_path:
            tg_ok = tg_send_photo(tg_text, img_path, "📰 اقرأ المزيد", item["link"])
            fb_ok = post_fb_photo(fb_text, img_path)
            try:
                os.remove(img_path)
            except Exception:
                pass
        else:
            tg_ok = tg_send_message(tg_text, "📰 اقرأ المزيد", item["link"])
            fb_ok = post_fb_text(fb_text, item["link"])

        if tg_ok or fb_ok:
            if "sent_news" not in state:
                state["sent_news"] = []
            state["sent_news"].append(news_id)
            # Keep only last 100 news IDs
            state["sent_news"] = state["sent_news"][-100:]
            sent_count += 1
            logger.info(f"✅ News posted: {item['title'][:60]}")
            time.sleep(3)  # Avoid rate limits


# ─── الدخول الرئيسي ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "alerts"

    # Load state
    state = load_state()

    if mode == "schedule":
        task_daily_schedule(state)
    elif mode == "alerts":
        task_match_alerts(state)
    elif mode == "news":
        task_post_news(state)
    elif mode == "all":
        task_daily_schedule(state)
        time.sleep(2)
        task_match_alerts(state)
        time.sleep(2)
        task_post_news(state)
    else:
        logger.error(f"Unknown mode: {mode}. Use: schedule | alerts | news | all")

    # Save state after every run
    save_state(state)
    logger.info("State saved. Done.")
