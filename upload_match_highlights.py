import os
import sys
import subprocess
import requests
import sqlite3
import json
from video_processor import process_video_for_shorts
from social_bot import post_fb_video
from youtube_uploader import upload_video as yt_upload

WEBSITE_URL = os.getenv("WEBSITE_URL", "https://yalla-shoot-today.vercel.app")
SPONSOR_URL = "https://www.profitablecpmrate.com/e4480b4a0a4ef0a7e842009f7c505039"
DB_PATH    = os.path.join(os.path.dirname(__file__), "matches.db")

def upload_video(match_id, team_a, team_b, video_url):
    print(f"Downloading video from {video_url}...")
    temp_file = f"/tmp/{match_id}.mp4"
    temp_shorts_file = f"/tmp/{match_id}_shorts.mp4"
    
    try:
        subprocess.run(["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", "-o", temp_file, video_url], check=True)
    except Exception as e:
        print(f"Failed to download video: {e}")
        return
        
    if not os.path.exists(temp_file):
        print("Video file not found after download.")
        return
        
    # Process video into 9:16 Shorts/Reels/TikTok vertical clip with copyright evasion
    title_text = f"{team_a} VS {team_b} | أهداف المباراة"
    shorts_success = process_video_for_shorts(temp_file, temp_shorts_file, title=title_text)
    
    video_to_upload = temp_shorts_file if shorts_success else temp_file

    desc = (
        f"🎬 ملخص وأهداف مباراة {team_a} ضد {team_b} 🤯\n\n"
        f"🔴 شاهد المزيد وتابع البث المباشر:\n{WEBSITE_URL}\n"
        f"🎁 توقع واربح:\n{SPONSOR_URL}\n\n"
        f"#{team_a.replace(' ', '_')} #{team_b.replace(' ', '_')} #يلا_شوت #مباريات_اليوم #كرة_القدم"
    )

    print(f"Uploading highlight video to Facebook for match {match_id}...")
    try:
        post_fb_video(desc, video_to_upload)
    except Exception as e:
        print(f"Error uploading to Facebook: {e}")

    # Upload to YouTube Shorts
    if shorts_success:
        try:
            print("Attempting automatic upload to YouTube Shorts...")
            yt_title = f"أهداف مباراة {team_a} ضد {team_b} 🔥 #Shorts #يلا_شوت"
            yt_upload(temp_shorts_file, yt_title, desc)
        except Exception as yt_err:
            print(f"YouTube Shorts auto-upload skipped or error: {yt_err}")

    # Cleanup
    for p in [temp_file, temp_shorts_file]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python upload_match_highlights.py <match_id> <team_a> <team_b> <video_url>")
        sys.exit(1)
    upload_video(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
