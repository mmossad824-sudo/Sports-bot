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

def run_ffmpeg_stream(stream_url: str, score_file_path: str):
    """Run FFmpeg to stream scoreboard to the given RTMP URL."""
    # Ensure score file exists
    if not os.path.exists(score_file_path):
        with open(score_file_path, "w", encoding="utf-8") as f:
            f.write("تبدأ قريباً...")

    filter_complex = (
        f"drawtext=fontfile='{FONT_PATH}':textfile='{score_file_path}':reload=1:"
        f"fontcolor=white:fontsize=80:x=(w-text_w)/2:y=(h-text_h)/2:"
        f"box=1:boxcolor=black@0.6:boxborderw=20,format=yuv420p"
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
        desc = f"لمشاهدة البث المباشر للمباراة كاملة وبدون تقطيع، تفضل بزيارة موقعنا:\n👉 {WEBSITE_URL}\n\n#يلا_شوت #بث_مباشر"
        
        # 1. Create Live Video
        stream_url, live_vid_id = start_facebook_live(title, desc)
        if not stream_url:
            sys.exit(1)
            
        # 2. Start FFmpeg
        proc = run_ffmpeg_stream(stream_url, score_file)
        
        # 3. Save metadata to stop it later
        with open(meta_file, "w") as f:
            json.dump({"pid": proc.pid, "live_video_id": live_vid_id}, f)
            
        logger.info(f"Live stream started for {match_id} with PID {proc.pid}")
        
    elif action == "stop":
        if os.path.exists(meta_file):
            with open(meta_file, "r") as f:
                data = json.load(f)
            pid = data.get("pid")
            vid_id = data.get("live_video_id")
            
            # Kill FFmpeg
            if pid:
                try:
                    os.kill(pid, 15) # SIGTERM
                    logger.info(f"Killed FFmpeg PID {pid}")
                except ProcessLookupError:
                    pass
                    
            # End FB Live
            if vid_id:
                end_facebook_live(vid_id)
                
            # Cleanup
            for fpath in [meta_file, score_file]:
                if os.path.exists(fpath):
                    os.remove(fpath)
                    
        logger.info(f"Live stream stopped for {match_id}")
