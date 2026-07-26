#!/usr/bin/env python3
"""
start_live.py — يفتح بث يوتيوب مع أسماء الفرق والنقاط والصوت اللانهائي
Usage: python3 start_live.py "فريق أ" "فريق ب"
"""
import os, sys, json, subprocess, signal
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(BASE_DIR, "Cairo-Bold.ttf")
BG   = os.path.join(BASE_DIR, "assets", "stadium_bg.png")
SFX  = os.path.join(BASE_DIR, "assets", "crowd.mp3")
WEBSITE = os.getenv("WEBSITE_URL", "yalla-shoot-today.vercel.app").replace("https://", "")
PID_FILE  = "/tmp/ys_ffmpeg.pid"
META_FILE = "/tmp/ys_live_meta.json"
SCORE_FILE = "/tmp/ys_score.txt"

def start(team_a: str, team_b: str):
    from youtube_uploader import create_youtube_live

    title = f"🔴 {team_a} ضد {team_b} | بث مباشر يلا شوت"
    desc  = (
        f"🔴 {team_a} ضد {team_b} — بث مباشر\n\n"
        f"📺 شاهد جدول المباريات:\n{WEBSITE}\n\n"
        f"#يلا_شوت #بث_مباشر #{team_a.replace(' ','_')} #{team_b.replace(' ','_')}"
    )

    print(f"⏳ إنشاء بث يوتيوب: {team_a} ضد {team_b} ...")
    result = create_youtube_live(title, desc)
    if not result:
        print("❌ فشل إنشاء البث على يوتيوب")
        sys.exit(1)

    rtmp_full   = result["rtmp_full"]
    broadcast_id = result["broadcast_id"]
    watch_url   = result["watch_url"]
    print(f"✅ البث جاهز | Watch: {watch_url}")

    # Write initial score
    with open(SCORE_FILE, "w", encoding="utf-8") as f:
        f.write("0 - 0")

    # Build FFmpeg command
    # -stream_loop -1 يجعل الصوت يتكرر لانهائياً
    cmd = [
        "ffmpeg", "-y",
        "-re",
        "-loop", "1", "-i", BG,
        "-stream_loop", "-1", "-i", SFX,
        "-vf",
        (
            f"drawtext=fontfile='{FONT}':text='{team_a}':fontcolor=white:fontsize=60:"
            f"x=80:y=75:box=1:boxcolor=black@0.75:boxborderw=18,"

            f"drawtext=fontfile='{FONT}':text='VS':fontcolor=#00FF88:fontsize=55:"
            f"x=(w-text_w)/2:y=80:box=1:boxcolor=black@0.75:boxborderw=15,"

            f"drawtext=fontfile='{FONT}':text='{team_b}':fontcolor=white:fontsize=60:"
            f"x=w-text_w-80:y=75:box=1:boxcolor=black@0.75:boxborderw=18,"

            f"drawtext=fontfile='{FONT}':textfile='{SCORE_FILE}':reload=1:"
            f"fontcolor=#00FF88:fontsize=130:x=(w-text_w)/2:y=(h-text_h)/2-70:"
            f"box=1:boxcolor=black@0.8:boxborderw=28,"

            f"drawtext=fontfile='{FONT}':text='المباراة غير منقولة هنا - الرابط في الوصف':"
            f"fontcolor=yellow:fontsize=42:x=(w-text_w)/2:y=h-165:"
            f"box=1:boxcolor=black@0.8:boxborderw=12,"

            f"drawtext=fontfile='{FONT}':text='{WEBSITE}':"
            f"fontcolor=white:fontsize=38:x=(w-text_w)/2:y=h-105:"
            f"box=1:boxcolor=#0055CC@0.9:boxborderw=12,"

            "format=yuv420p"
        ),
        "-c:v", "libx264", "-preset", "ultrafast", "-r", "15",
        "-b:v", "800k", "-maxrate", "800k", "-bufsize", "1600k", "-g", "30",
        "-c:a", "aac", "-b:a", "128k",
        "-f", "flv", rtmp_full
    ]

    print("⏳ بدء FFmpeg...")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=open("/tmp/ys_ffmpeg.log", "w"))
    print(f"✅ FFmpeg PID: {proc.pid}")

    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))

    with open(META_FILE, "w") as f:
        json.dump({**result, "pid": proc.pid, "team_a": team_a, "team_b": team_b}, f)

    print(f"\n🔴 البث شغال الآن!")
    print(f"   ▶️  رابط المشاهدة: {watch_url}")
    print(f"   📄 لوقف البث: python3 start_live.py stop")


def stop():
    if not os.path.exists(META_FILE):
        print("لا يوجد بث نشط")
        return

    with open(META_FILE) as f:
        meta = json.load(f)

    pid = meta.get("pid")
    broadcast_id = meta.get("broadcast_id")

    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"✅ تم إيقاف FFmpeg (PID {pid})")
        except ProcessLookupError:
            pass

    if broadcast_id:
        from youtube_uploader import end_youtube_live
        end_youtube_live(broadcast_id)
        print(f"✅ تم إنهاء البث على يوتيوب ({broadcast_id})")

    for f in [META_FILE, PID_FILE, SCORE_FILE]:
        try: os.remove(f)
        except: pass
    print("✅ البث أُغلق بالكامل")


def status():
    if not os.path.exists(PID_FILE):
        print("لا يوجد بث نشط")
        return
    pid = int(open(PID_FILE).read())
    try:
        os.kill(pid, 0)
        meta = json.load(open(META_FILE))
        print(f"🔴 البث شغال | {meta.get('team_a')} ضد {meta.get('team_b')}")
        print(f"   Watch: {meta.get('watch_url')}")
        print(f"   FFmpeg PID: {pid}")
    except ProcessLookupError:
        print("❌ FFmpeg توقف")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 start_live.py <start 'فريق أ' 'فريق ب'|stop|status>")
        sys.exit(1)

    action = sys.argv[1]
    if action == "start":
        team_a = sys.argv[2] if len(sys.argv) > 2 else "يلا شوت"
        team_b = sys.argv[3] if len(sys.argv) > 3 else "بث مباشر"
        start(team_a, team_b)
    elif action == "stop":
        stop()
    elif action == "status":
        status()
    else:
        print("Unknown action. Use: start / stop / status")
