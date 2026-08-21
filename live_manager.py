#!/usr/bin/env python3
"""
live_manager.py — نظام البث المباشر الذكي ليلا شوت
- يختار أفضل مباراة (الأكثر جمهورًا عربيًا)
- يحمّل شعارات الفريقين
- يفتح بث يوتيوب واحد فقط
- يعيد الفيديو حتى تنتهي المباراة
- يوقف البث تلقائياً عند انتهاء المباراة
"""

import os, sys, json, time, signal, subprocess, requests, logging, threading
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from youtube_uploader import get_access_token

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("LiveManager")

# ── إعدادات ──────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
FONT_PATH   = os.path.join(BASE_DIR, "Cairo-Bold.ttf")
CROWD_AUDIO = os.path.join(BASE_DIR, "assets", "crowd.mp3")
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://yalla-shoot-today.vercel.app")
WEBSITE     = WEBSITE_URL.replace("https://", "").replace("http://", "")
HF_API      = os.getenv("HF_API_URL", "https://mmossad824-sports-bot.hf.space")

META_FILE   = "/tmp/ys_live_meta.json"
PID_FILE    = "/tmp/ys_live_pid"
LOG_FILE    = "/tmp/ys_live_ffmpeg.log"
LOGO_A_PATH = "/tmp/ys_logo_a.png"
LOGO_B_PATH = "/tmp/ys_logo_b.png"
SCORE_FILE  = "/tmp/ys_live_score.txt"
TEAM_A_FILE = "/tmp/ys_live_team_a.txt"
TEAM_B_FILE = "/tmp/ys_live_team_b.txt"

# ── قائمة أولويات الأندية/المنتخبات حسب الجمهور العربي ──────────────────────
ARAB_PRIORITY = {
    # المنتخبات العربية — أعلى أولوية
    "مصر": 100, "المغرب": 95, "الجزائر": 90, "تونس": 88, "السعودية": 85,
    "قطر": 82, "الإمارات": 80, "ليبيا": 78, "سوريا": 76,
    "egypt": 100, "morocco": 95, "algeria": 90, "tunisia": 88, "saudi": 85,
    "qatar": 82, "uae": 80, "libya": 78, "syria": 76,
    # الأندية السعودية والخليجية
    "الهلال": 82, "النصر": 80, "الاتحاد": 76, "الشباب": 73, "القادسية": 68,
    "al hilal": 82, "al nassr": 80, "al ittihad": 76,
    # الأندية المصرية
    "الأهلي": 88, "الزمالك": 84, "الاهلي": 88, "بيراميدز": 70,
    "al ahly": 88, "zamalek": 84,
    # الأندية الأوروبية الكبيرة (جمهور عربي ضخم)
    "ريال مدريد": 90, "برشلونة": 88, "ليفربول": 80, "مانشستر سيتي": 78,
    "مانشستر يونايتد": 75, "باريس سان جيرمان": 76, "باريس": 76,
    "أتلتيكو مدريد": 72, "أتليتكو": 72, "أرسنال": 74, "تشيلسي": 72,
    "بايرن": 70, "يوفنتوس": 68, "انتر ميلان": 65, "ميلان": 65,
    "بوروسيا دورتموند": 63, "بنفيكا": 60,
    "real madrid": 90, "barcelona": 88, "liverpool": 80, "manchester city": 78,
    "manchester united": 75, "paris saint-germain": 76, "psg": 76,
    "atletico madrid": 72, "arsenal": 74, "chelsea": 72,
    "bayern": 70, "juventus": 68, "inter milan": 65, "ac milan": 65,
    "borussia dortmund": 63, "benfica": 60,
    # بطولات مميزة
    "دوري أبطال": 95, "champions league": 95,
    "يورو": 92, "كأس العالم": 99, "world cup": 99, "كأس أمم أفريقيا": 90,
}

# الحد الأدنى للأولوية لكي يُنشأ بث يوتيوب تفاعلي (فرق مشهورة فقط - رُفع لحماية القناة)
MIN_PRIORITY_FOR_YT = 80
# الحد الأقصى لبثوث يوتيوب في اليوم الواحد — مباراة واحدة فقط لحماية القناة الجديدة
MAX_YT_STREAMS_PER_DAY = 1
# ملف عداد البثوص اليومية
YT_DAILY_COUNT_FILE = "/tmp/ys_yt_daily_count.json"

def get_match_priority(team_a: str, team_b: str) -> int:
    """تقييم أولوية المباراة حسب الجمهور العربي"""
    score = 0
    combined = (team_a + " " + team_b).lower()
    for keyword, pts in ARAB_PRIORITY.items():
        if keyword.lower() in combined:
            score = max(score, pts)
    return score


def download_logo(url: str, path: str) -> bool:
    """تحميل شعار الفريق وتحويله لـ PNG بحجم مناسب"""
    if not url or not url.startswith("http"):
        return False
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return False
        # Save raw image
        raw_path = path + ".raw"
        with open(raw_path, "wb") as f:
            f.write(r.content)
        # Convert to 120x120 PNG using ffmpeg
        result = subprocess.run([
            "ffmpeg", "-y", "-i", raw_path,
            "-vf", "scale=120:120:force_original_aspect_ratio=decrease,pad=120:120:(ow-iw)/2:(oh-ih)/2:color=0x00000000",
            "-f", "apng", path
        ], capture_output=True, timeout=10)
        os.remove(raw_path)
        return os.path.exists(path)
    except Exception as e:
        logger.warning(f"Failed to download logo from {url}: {e}")
        return False


def count_todays_yt_streams() -> int:
    """كم مرة شغّلنا بث يوتيوب اليوم؟"""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if not os.path.exists(YT_DAILY_COUNT_FILE):
        return 0
    try:
        data = json.load(open(YT_DAILY_COUNT_FILE))
        if data.get("date") != today:
            return 0  # يوم جديد
        return data.get("count", 0)
    except Exception:
        return 0


def increment_todays_yt_count():
    """زيادة عداد بثوث اليوم"""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    count = count_todays_yt_streams() + 1
    with open(YT_DAILY_COUNT_FILE, "w") as f:
        json.dump({"date": today, "count": count}, f)
    logger.info(f"📊 اليوم تم فتح {count} بث يوتيوب.")


def pick_best_match() -> dict | None:
    """جلب المباريات الحالية واختيار أفضل واحدة — للفرق المشهورة فقط"""
    try:
        r = requests.get(f"{HF_API}/api/matches", timeout=10)
        if r.status_code != 200:
            logger.error(f"Failed to fetch matches: {r.status_code}")
            return None
        matches = r.json()
    except Exception as e:
        logger.error(f"Cannot fetch matches: {e}")
        return None

    # Filter: live or starting in < 30 min + minimum popularity
    candidates = []
    for m in matches:
        status = (m.get("status") or "").lower()
        if status in ("live", "1st half", "2nd half", "half time", "مباشر",
                      "الشوط الأول", "الشوط الثاني", "استراحة", "جاري",
                      "جارية الآن"):
            priority = get_match_priority(m.get("teamA", ""), m.get("teamB", ""))
            if priority >= MIN_PRIORITY_FOR_YT:  # فقط الفرق المشهورة
                candidates.append((priority, m))

    if not candidates:
        logger.info("No popular live matches found for YT stream.")
        return None

    # Sort by priority descending, return top match
    candidates.sort(key=lambda x: x[0], reverse=True)
    score, match = candidates[0]
    
    # We should also return the stream URL so we can use it in the description/comment
    logger.info(f"Selected: {match['teamA']} vs {match['teamB']} (priority={score})")
    return match


def auto_manage_live_streams():
    """
    الدالة الرئيسية للجدولة التلقائية:
    - تتحقق من حد البثوث اليومية (MAX_YT_STREAMS_PER_DAY)
    - تختار أفضل مباراة مشهورة جارية
    - تشغل البث إذا لم يكن يعمل
    - توقف البث إذا انتهت المباراة
    """
    import sqlite3 as _sq
    from scraper import DB_PATH as _DB

    # هل البث شغال بالفعل؟
    if is_stream_alive():
        logger.info("auto_manage: stream already running, skipping.")
        return

    # هل تجاوزنا الحد اليومي؟
    today_count = count_todays_yt_streams()
    if today_count >= MAX_YT_STREAMS_PER_DAY:
        logger.info(f"auto_manage: daily limit reached ({today_count}/{MAX_YT_STREAMS_PER_DAY}).")
        return

    # اختر أفضل مباراة
    match = pick_best_match()
    if not match:
        logger.info("auto_manage: no popular match to stream.")
        return

    real_match_link = match.get("url", "")
    if real_match_link:
        # If the URL is relative, prepend the website domain
        if real_match_link.startswith("/"):
            real_match_link = f"https://{WEBSITE}" + real_match_link
    else:
        real_match_link = f"https://{WEBSITE}"

    logger.info(f"🚀 auto_manage: Starting YT stream for {match['teamA']} vs {match['teamB']}")
    meta = start_stream(
        team_a=match.get("teamA", ""),
        team_b=match.get("teamB", ""),
        score=f"{match.get('scoreA','0')} - {match.get('scoreB','0')}",
        logo_a_url=match.get("logoA", ""),
        logo_b_url=match.get("logoB", ""),
        match_id=match.get("id", ""),
        real_match_link=real_match_link
    )
    if meta:
        increment_todays_yt_count()
        # Send hype notification
        from social_bot import send_telegram_alert
        hype_msg = f"🔥 بدأ البث التفاعلي الآن لمباراة {match.get('teamA')} ضد {match.get('teamB')}!\n\n📺 لمشاهدة البث الحقيقي للمباراة بدون تقطيع: {real_match_link}"
        send_telegram_alert(hype_msg)
        logger.info(f"✅ auto_manage: stream live at {meta['watch_url']}")
        # Start watch loop in a daemon thread so scheduler returns immediately
        threading.Thread(target=watch_loop, daemon=True).start()


def build_ffmpeg_cmd(rtmp_url: str) -> list:
    """بناء أمر FFmpeg مع الشعارات والنصوص"""
    has_logo_a = os.path.exists(LOGO_A_PATH)
    has_logo_b = os.path.exists(LOGO_B_PATH)

    # Base drawtext filters (applied to video)
    drawtext_filters = [
        # Team A name (top left)
        f"drawtext=fontfile='{FONT_PATH}':textfile='{TEAM_A_FILE}':reload=1:"
        f"fontcolor=white:fontsize=55:x=160:y=72:"
        f"box=1:boxcolor=black@0.8:boxborderw=16",
        # VS separator
        f"drawtext=fontfile='{FONT_PATH}':text='VS':"
        f"fontcolor=0x00FF88:fontsize=52:x=(w-text_w)/2:y=78:"
        f"box=1:boxcolor=black@0.8:boxborderw=14",
        # Team B name (top right)
        f"drawtext=fontfile='{FONT_PATH}':textfile='{TEAM_B_FILE}':reload=1:"
        f"fontcolor=white:fontsize=55:x=w-text_w-160:y=72:"
        f"box=1:boxcolor=black@0.8:boxborderw=16",
        # Score center
        f"drawtext=fontfile='{FONT_PATH}':textfile='{SCORE_FILE}':reload=1:"
        f"fontcolor=0x00FF88:fontsize=150:x=(w-text_w)/2:y=(h-text_h)/2-80:"
        f"box=1:boxcolor=black@0.85:boxborderw=30",
        # Watch Live text
        f"drawtext=fontfile='{FONT_PATH}':text='Watch Live HD - No Buffering':"
        f"fontcolor=yellow:fontsize=42:x=(w-text_w)/2:y=h-185:"
        f"box=1:boxcolor=black@0.75:boxborderw=12",
        # Website URL
        f"drawtext=fontfile='{FONT_PATH}':text='{WEBSITE}':"
        f"fontcolor=white:fontsize=40:x=(w-text_w)/2:y=h-115:"
        f"box=1:boxcolor=0x0044CC@0.9:boxborderw=13",
        "format=yuv420p",
    ]
    dt_chain = ",".join(drawtext_filters)

    has_audio = os.path.exists(CROWD_AUDIO)
    if has_audio:
        audio_inputs = ["-stream_loop", "-1", "-i", CROWD_AUDIO]
    else:
        audio_inputs = ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]

    # Base inputs
    inputs = [
        "ffmpeg", "-y",
        "-re",  # Real-time speed — CRITICAL to prevent YouTube disconnect
        "-f", "lavfi", "-i", "color=c=0x0d1b2a:s=1920x1080:r=25:d=36000",
    ] + audio_inputs

    if has_logo_a:
        inputs += ["-loop", "1", "-i", LOGO_A_PATH]
    if has_logo_b:
        inputs += ["-loop", "1", "-i", LOGO_B_PATH]

    # Build filter_complex or simple -vf
    if has_logo_a or has_logo_b:
        # Logo inputs start at index 2
        idx = 2
        chains = []
        prev = "[0:v]"
        if has_logo_a:
            nxt = f"[ov{idx}]"
            chains.append(f"{prev}[{idx}:v]overlay=20:15{nxt}")
            prev = nxt
            idx += 1
        if has_logo_b:
            nxt = f"[ov{idx}]"
            chains.append(f"{prev}[{idx}:v]overlay=W-140:15{nxt}")
            prev = nxt
        # Apply drawtext to final overlay result
        chains.append(f"{prev}{dt_chain}[vout]")
        filter_complex = ";".join(chains)
        vf_args = ["-filter_complex", filter_complex, "-map", "[vout]", "-map", "1:a"]
    else:
        vf_args = ["-vf", dt_chain]

    output_args = [
        "-c:v", "libx264", "-preset", "ultrafast",
        "-b:v", "1500k", "-maxrate", "1500k", "-bufsize", "3000k",
        "-g", "50", "-keyint_min", "25",
        "-c:a", "aac", "-b:a", "128k",
        "-f", "flv",
        "-flvflags", "no_duration_filesize",  # Better RTMP compatibility
        rtmp_url
    ]

    return inputs + vf_args + output_args



def start_stream(team_a: str, team_b: str, score: str = "0 - 0",
                 logo_a_url: str = "", logo_b_url: str = "",
                 match_id: str = "test", real_match_link: str = "") -> dict | None:
    """بدء البث على يوتيوب وإرجاع بيانات البث"""
    from youtube_uploader import create_youtube_live, post_youtube_comment

    # Write text files
    with open(TEAM_A_FILE, "w", encoding="utf-8") as f: f.write(team_a)
    with open(TEAM_B_FILE, "w", encoding="utf-8") as f: f.write(team_b)
    with open(SCORE_FILE,  "w", encoding="utf-8") as f: f.write(score)

    # Download logos
    logger.info("⬇️ Downloading team logos...")
    logo_a_ok = download_logo(logo_a_url, LOGO_A_PATH)
    logo_b_ok = download_logo(logo_b_url, LOGO_B_PATH)
    logger.info(f"Logos: A={'✅' if logo_a_ok else '❌'} | B={'✅' if logo_b_ok else '❌'}")

    # Create YouTube broadcast
    title = f"🔴 {team_a} vs {team_b} | بث مباشر | {WEBSITE}"
    desc  = (
        f"🔴 {team_a} ضد {team_b} — بث مباشر\n\n"
        f"📺 شاهد المباراة بجودة HD بدون تقطيع:\n👉 {real_match_link if real_match_link else WEBSITE_URL}\n\n"
        f"⚽ يلا شوت — أفضل موقع للمباريات المباشرة: {WEBSITE}\n\n"
        f"#يلا_شوت #بث_مباشر #{team_a.replace(' ','_')} #{team_b.replace(' ','_')}"
    )

    logger.info(f"📡 Creating YouTube broadcast: {team_a} vs {team_b}")
    result = create_youtube_live(title, desc)
    if not result:
        logger.error("❌ Failed to create YouTube broadcast")
        return None

    rtmp = result["rtmp_full"]
    watch_url = result["watch_url"]
    broadcast_id = result["broadcast_id"]
    logger.info(f"✅ Broadcast ready: {watch_url}")

    if broadcast_id:
        comment_text = f"🔥 شاهد البث الحقيقي للمباراة (بدون تقطيع) عبر الرابط التالي:\n👉 {real_match_link if real_match_link else WEBSITE_URL}"
        logger.info("📌 Posting pinned comment to YouTube...")
        post_youtube_comment(broadcast_id, comment_text)

    # Build & launch FFmpeg
    cmd = build_ffmpeg_cmd(rtmp)
    logger.info("🎬 Starting FFmpeg...")
    proc = subprocess.Popen(cmd, stdout=open(LOG_FILE, "w"), stderr=subprocess.STDOUT)
    logger.info(f"✅ FFmpeg PID: {proc.pid}")

    meta = {
        "pid": proc.pid,
        "broadcast_id": broadcast_id,
        "watch_url": watch_url,
        "match_id": match_id,
        "team_a": team_a,
        "team_b": team_b,
        "started_at": datetime.now().isoformat()
    }
    with open(META_FILE, "w") as f: json.dump(meta, f, ensure_ascii=False)
    with open(PID_FILE,  "w") as f: f.write(str(proc.pid))

    # Transition broadcast to 'testing' after FFmpeg starts sending data, then 'live'
    def _go_live():
        logger.info("⏳ Waiting for stream to become active...")
        time.sleep(6)
        if not is_stream_alive():
            logger.warning("FFmpeg died before transition")
            return
        
        token = get_access_token()
        if token:
            from youtube_uploader import transition_broadcast
            logger.info("⏳ Transitioning broadcast to 'testing'...")
            ok = transition_broadcast(broadcast_id, "testing", token)
            if ok:
                time.sleep(5)
                logger.info("⏳ Transitioning broadcast to 'live'...")
                transition_broadcast(broadcast_id, "live", token)
            else:
                logger.warning("⚠️ Could not transition to testing. Will try live directly in a few seconds...")
                time.sleep(5)
                transition_broadcast(broadcast_id, "live", token)

    threading.Thread(target=_go_live, daemon=True).start()

    # Update HF DB
    try:
        stream_sources = [{"name": "🔴 يوتيوب لايف", "type": "iframe", "url": watch_url}]
        requests.post(
            f"{HF_API}/api/matches/{match_id}/update",
            json={"stream_type": "multi", "stream_url": json.dumps(stream_sources)},
            timeout=10
        )
        logger.info("✅ Stream URL saved to HF database")
    except Exception as e:
        logger.warning(f"Could not update HF DB: {e}")

    return meta


def stop_stream():
    """إيقاف البث الحالي"""
    if not os.path.exists(META_FILE):
        logger.info("No active stream.")
        return

    meta = json.load(open(META_FILE))
    pid = meta.get("pid")
    broadcast_id = meta.get("broadcast_id")

    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            logger.info(f"✅ FFmpeg stopped (PID {pid})")
        except ProcessLookupError:
            pass

    if broadcast_id:
        from youtube_uploader import end_youtube_live
        end_youtube_live(broadcast_id)
        logger.info(f"✅ YouTube broadcast ended ({broadcast_id})")

    for f in [META_FILE, PID_FILE, SCORE_FILE, TEAM_A_FILE, TEAM_B_FILE, LOGO_A_PATH, LOGO_B_PATH, LOG_FILE]:
        try: os.remove(f)
        except: pass
    logger.info("🔴 Stream fully stopped.")


def is_stream_alive() -> bool:
    """التحقق أن FFmpeg لا يزال يعمل"""
    if not os.path.exists(PID_FILE):
        return False
    pid = int(open(PID_FILE).read().strip())
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def watch_loop():
    """حلقة مراقبة تعيد تشغيل البث لو وقف وتوقفه لو انتهت المباراة"""
    logger.info("🔁 Starting watch loop...")
    restart_count = 0
    MAX_RESTARTS = 10

    while True:
        time.sleep(30)

        if not os.path.exists(META_FILE):
            logger.info("No stream meta, watch loop exiting.")
            break

        meta = json.load(open(META_FILE))
        match_id = meta.get("match_id")

        # Check if match is still live
        try:
            r = requests.get(f"{HF_API}/api/matches", timeout=10)
            matches = r.json()
            match_data = next((m for m in matches if m.get("id") == match_id), None)

            if match_data:
                status = (match_data.get("status") or "").lower()
                score_a = match_data.get("scoreA", "0")
                score_b = match_data.get("scoreB", "0")

                # Update score file live
                with open(SCORE_FILE, "w", encoding="utf-8") as f:
                    f.write(f"{score_a} - {score_b}")

                if status in ("finished", "انتهت", "full time", "ft"):
                    logger.info(f"Match finished ({score_a}-{score_b}). Stopping stream.")
                    stop_stream()
                    break

        except Exception as e:
            logger.warning(f"Could not check match status: {e}")

        # Check if FFmpeg died and restart
        if not is_stream_alive():
            restart_count += 1
            logger.warning(f"⚠️ FFmpeg died! Restart #{restart_count}/{MAX_RESTARTS}")
            if restart_count > MAX_RESTARTS:
                logger.error("Too many restarts. Giving up.")
                stop_stream()
                break

            if os.path.exists(META_FILE):
                meta = json.load(open(META_FILE))
                old_broadcast_id = meta.get("broadcast_id")
                team_a = meta.get("team_a", "")
                team_b = meta.get("team_b", "")

                # Re-create broadcast (old one is dead)
                from youtube_uploader import create_youtube_live
                title = f"🔴 {team_a} vs {team_b} | بث مباشر | {WEBSITE}"
                desc = f"🔴 {team_a} ضد {team_b}\n📺 {WEBSITE_URL}"
                new_result = create_youtube_live(title, desc)
                if new_result:
                    rtmp = new_result["rtmp_full"]
                    meta["broadcast_id"] = new_result["broadcast_id"]
                    meta["watch_url"] = new_result["watch_url"]
                    cmd = build_ffmpeg_cmd(rtmp)
                    proc = subprocess.Popen(cmd, stdout=open(LOG_FILE, "w"), stderr=subprocess.STDOUT)
                    meta["pid"] = proc.pid
                    with open(META_FILE, "w") as f: json.dump(meta, f, ensure_ascii=False)
                    with open(PID_FILE,  "w") as f: f.write(str(proc.pid))
                    logger.info(f"🔄 Stream restarted: {new_result['watch_url']}")
        else:
            restart_count = 0  # Reset counter if healthy


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "auto"

    if action == "stop":
        stop_stream()

    elif action == "status":
        if is_stream_alive():
            meta = json.load(open(META_FILE))
            logger.info(f"🔴 LIVE: {meta['team_a']} vs {meta['team_b']}")
            logger.info(f"   Watch: {meta['watch_url']}")
            logger.info(f"   PID: {meta['pid']}")
        else:
            logger.info("No active stream")

    elif action == "test":
        # اختبار بفريقين محددين
        team_a = sys.argv[2] if len(sys.argv) > 2 else "ريال مدريد"
        team_b = sys.argv[3] if len(sys.argv) > 3 else "برشلونة"
        logo_a = sys.argv[4] if len(sys.argv) > 4 else "https://crests.football-data.org/86.png"
        logo_b = sys.argv[5] if len(sys.argv) > 5 else "https://crests.football-data.org/81.png"

        if is_stream_alive():
            logger.warning("Stream already running! Stop it first with: python3 live_manager.py stop")
            sys.exit(1)

        meta = start_stream(team_a, team_b, "0 - 0", logo_a, logo_b, "test")
        if meta:
            logger.info(f"\n🔴 ══ البث شغال! ══")
            logger.info(f"   ▶️  {meta['watch_url']}")
            logger.info(f"   FFmpeg PID: {meta['pid']}")
            logger.info(f"\n   للإيقاف: python3 live_manager.py stop")
            # Start watch loop in background
            watch_loop()

    elif action == "auto":
        # الوضع التلقائي: يختار أفضل مباراة
        if is_stream_alive():
            logger.info("Stream already running.")
            sys.exit(0)

        match = pick_best_match()
        if not match:
            logger.info("No suitable match found. Exiting.")
            sys.exit(0)

        meta = start_stream(
            team_a=match.get("teamA", ""),
            team_b=match.get("teamB", ""),
            score=f"{match.get('scoreA','0')} - {match.get('scoreB','0')}",
            logo_a_url=match.get("logoA", ""),
            logo_b_url=match.get("logoB", ""),
            match_id=match.get("id", "")
        )
        if meta:
            logger.info(f"🔴 Auto stream started: {meta['watch_url']}")
            watch_loop()
