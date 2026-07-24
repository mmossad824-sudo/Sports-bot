import os
import sys
import json
import time
import subprocess
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("live_streamer")

FB_PAGE_TOKEN = os.getenv("FB_PAGE_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://yalla-shoot-today.vercel.app")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
BG_IMAGE = os.path.join(ASSETS_DIR, "stadium_bg.png")
CROWD_AUDIO = os.path.join(ASSETS_DIR, "crowd.mp3")
FONT_PATH = os.path.join(BASE_DIR, "Cairo-Bold.ttf")

def start_facebook_live(title: str, description: str):
    """Create a Live Video on Facebook Page and return (stream_url, live_video_id)."""
    if not FB_PAGE_TOKEN or not FB_PAGE_ID:
        logger.error("Facebook credentials missing.")
        return None, None
        
    url = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/live_videos"
    payload = {
        "access_token": FB_PAGE_TOKEN,
        "status": "LIVE_NOW",
        "title": title,
        "description": description
    }
    try:
        r = requests.post(url, data=payload, timeout=15)
        data = r.json()
        if "stream_url" in data and "id" in data:
            return data["stream_url"], data["id"]
        else:
            logger.error(f"Failed to create live video: {data}")
            return None, None
    except Exception as e:
        logger.error(f"Exception creating FB live video: {e}")
        return None, None

def end_facebook_live(live_video_id: str):
    """End a Live Video on Facebook."""
    if not FB_PAGE_TOKEN or not live_video_id:
        return
    url = f"https://graph.facebook.com/v21.0/{live_video_id}"
    payload = {
        "access_token": FB_PAGE_TOKEN,
        "end_live_video": "true"
    }
    try:
        requests.post(url, data=payload, timeout=15)
        logger.info(f"Ended Facebook live video {live_video_id}")
    except Exception as e:
        logger.error(f"Failed to end FB live video: {e}")


def start_youtube_live(title: str, description: str):
    """Create a YouTube Live Broadcast + Stream and return (rtmp_full_url, broadcast_id)."""
    try:
        from youtube_uploader import create_youtube_live
        result = create_youtube_live(title, description)
        if result:
            logger.info(f"✅ YouTube Live ready: {result['watch_url']}")
            return result["rtmp_full"], result["broadcast_id"], result["watch_url"]
        else:
            logger.error("YouTube Live creation returned None.")
            return None, None, None
    except Exception as e:
        logger.error(f"Exception starting YouTube live: {e}")
        return None, None, None


def end_youtube_live(broadcast_id: str):
    """End a YouTube Live Broadcast."""
    if not broadcast_id:
        return
    try:
        from youtube_uploader import end_youtube_live as _end
        _end(broadcast_id)
    except Exception as e:
        logger.error(f"Failed to end YouTube live: {e}")


def run_ffmpeg_stream(stream_url: str, score_file_path: str):
    """Run FFmpeg to stream scoreboard to the given RTMP URL."""
    # Ensure score file exists
    if not os.path.exists(score_file_path):
        with open(score_file_path, "w", encoding="utf-8") as f:
            f.write("تبدأ قريباً...")

    filter_complex = (
        f"drawtext=fontfile='{FONT_PATH}':textfile='{score_file_path}':reload=1:"
        f"fontcolor=white:fontsize=80:x=(w-text_w)/2:y=(h-text_h)/2-50:"
        f"box=1:boxcolor=black@0.6:boxborderw=20,"
        f"drawtext=fontfile='{FONT_PATH}':text='المباراة غير منقولة هنا.. الرابط في الوصف':"
        f"fontcolor=yellow:fontsize=50:x=(w-text_w)/2:y=h-180:"
        f"box=1:boxcolor=black@0.8:boxborderw=15,"
        f"drawtext=fontfile='{FONT_PATH}':text='{WEBSITE_URL.replace('https://', '')}':"
        f"fontcolor=white:fontsize=45:x=(w-text_w)/2:y=h-100:"
        f"box=1:boxcolor=blue@0.6:boxborderw=15,format=yuv420p"
    )

    cmd = [
        "ffmpeg",
        "-re", # Read input at native frame rate
        "-loop", "1", "-i", BG_IMAGE,
        "-stream_loop", "-1", "-i", CROWD_AUDIO,
        "-filter_complex", filter_complex,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-b:v", "1500k",
        "-maxrate", "1500k",
        "-bufsize", "3000k",
        "-g", "60", # Keyframe interval (2 seconds at 30fps)
        "-c:a", "aac",
        "-b:a", "128k",
        "-f", "flv",
        stream_url
    ]

    logger.info("Starting FFmpeg stream...")
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python live_streamer.py <start|stop> <match_id> [team_a] [team_b]")
        sys.exit(1)
        
    action = sys.argv[1]
    match_id = sys.argv[2]
    
    score_file = os.path.join(BASE_DIR, f"live_score_{match_id}.txt")
    meta_file = os.path.join(BASE_DIR, f"live_meta_{match_id}.json")
    
    if action == "start":
        team_a = sys.argv[3] if len(sys.argv) > 3 else "فريق 1"
        team_b = sys.argv[4] if len(sys.argv) > 4 else "فريق 2"
        
        title = f"🔴 بث مباشر: {team_a} ضد {team_b}"
        desc = (
            f"🔴 بث مباشر: {team_a} ضد {team_b}\n\n"
            f"📺 شاهد المباراة بدون تقطيع:\n👉 {WEBSITE_URL}\n\n"
            f"#يلا_شوت #بث_مباشر #{team_a.replace(' ','_')} #{team_b.replace(' ','_')}"
        )

        meta = {}

        # ── 1. Try YouTube Live first (primary) ────────────────────────────────
        yt_rtmp, yt_broadcast_id, yt_watch_url = start_youtube_live(title, desc)
        if yt_rtmp:
            proc = run_ffmpeg_stream(yt_rtmp, score_file)
            meta["pid"] = proc.pid
            meta["yt_broadcast_id"] = yt_broadcast_id
            meta["yt_watch_url"] = yt_watch_url
            logger.info(f"✅ YouTube Live stream started | Watch: {yt_watch_url}")

            # Save YouTube stream URL to HF Space database
            hf_api = os.getenv("HF_API_URL", "https://mmossad824-sports-bot.hf.space")
            try:
                import json as _json
                stream_sources = [{"name": "🔴 يوتيوب لايف", "type": "iframe", "url": yt_watch_url}]
                requests.post(
                    f"{hf_api}/api/matches/{match_id}/update",
                    json={"stream_type": "multi", "stream_url": _json.dumps(stream_sources)},
                    timeout=15
                )
                logger.info("✅ YouTube Live URL saved to HF DB")
            except Exception as e:
                logger.warning(f"Could not update HF DB with YT URL: {e}")
        else:
            # ── 2. Fallback to Facebook Live ───────────────────────────────────
            logger.warning("YouTube Live failed — trying Facebook Live as fallback...")
            fb_rtmp, fb_vid_id = start_facebook_live(title, desc)
            if fb_rtmp:
                proc = run_ffmpeg_stream(fb_rtmp, score_file)
                meta["pid"] = proc.pid
                meta["live_video_id"] = fb_vid_id
                logger.info(f"✅ Facebook Live stream started | Video ID: {fb_vid_id}")
            else:
                logger.error("Both YouTube and Facebook Live failed. Exiting.")
                sys.exit(1)

        # Save metadata to stop it later
        with open(meta_file, "w") as f:
            json.dump(meta, f)

        logger.info(f"Live stream started for match {match_id} with PID {meta.get('pid')}")
        
    elif action == "stop":
        if os.path.exists(meta_file):
            with open(meta_file, "r") as f:
                data = json.load(f)
            pid = data.get("pid")
            fb_vid_id = data.get("live_video_id")
            yt_broadcast_id = data.get("yt_broadcast_id")

            # Kill FFmpeg
            if pid:
                try:
                    os.kill(pid, 15)  # SIGTERM
                    logger.info(f"Killed FFmpeg PID {pid}")
                except ProcessLookupError:
                    pass

            # End YouTube Live
            if yt_broadcast_id:
                end_youtube_live(yt_broadcast_id)

            # End Facebook Live
            if fb_vid_id:
                end_facebook_live(fb_vid_id)

            # Cleanup files
            for fpath in [meta_file, score_file]:
                if os.path.exists(fpath):
                    os.remove(fpath)

        logger.info(f"Live stream stopped for match {match_id}")

