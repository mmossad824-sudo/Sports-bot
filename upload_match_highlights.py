import os
from dotenv import load_dotenv
load_dotenv()
import sys
import subprocess
import requests
import sqlite3
import json
from video_processor import process_video_for_shorts
from social_bot import (
    post_fb_video, post_fb_comment,
    YT_CHANNEL_URL, TIKTOK_PROFILE_URL
)
from youtube_uploader import upload_video as yt_upload, post_youtube_comment

WEBSITE_URL = os.getenv("WEBSITE_URL", "https://yalla-shoot-today.vercel.app")
TELEGRAM_GROUP_URL = "https://t.me/yalla_shoot_today_Group"
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
        
    # Process for Facebook (Nuclear Evasion)
    print("Processing video for Facebook...")
    temp_fb_shorts = f"/tmp/{match_id}_fb_shorts.mp4"
    title_text = f"{team_a} VS {team_b} | أهداف المباراة"
    fb_success = process_video_for_shorts(temp_file, temp_fb_shorts, title=title_text, platform="facebook")
    video_to_upload_fb = temp_fb_shorts if fb_success else temp_file

    desc = (
        f"🚨🔥 شاهد الآن: ملخص وأهداف المباراة النارية بين {team_a} و {team_b} 🤯⚽\n"
        f"لا تفوت فرصة مشاهدة كل اللقطات الحاسمة والأهداف الخرافية من هذه المواجهة الكروية المثيرة!\n\n"
        f"📌 لمشاهدة المقطع بجودة عالية وصورة واضحة كاملة، بالإضافة للبث المباشر لكل المباريات بدون تقطيع، "
        f"تفضل بزيارة موقعنا الآن:\n🔗 {WEBSITE_URL}\n\n"
        f"📱 تابعنا على منصاتنا لتغطية حصرية 24/7:\n"
        f"💬 تليجرام: {TELEGRAM_GROUP_URL}\n"
        f"▶️ يوتيوب: {YT_CHANNEL_URL}\n"
        f"🎵 تيك توك: {TIKTOK_PROFILE_URL}\n\n"
        f"🎁 العب وتوقع واربح جوائز قيمة:\n"
        f"{SPONSOR_URL}\n\n"
        f"#{team_a.replace(' ', '_')} #{team_b.replace(' ', '_')} #يلا_شوت #مباريات_اليوم #كرة_القدم #أهداف_مجنونة #ملخص_مباراة"
    )

    comment_text = (
        f"📌 لمشاهدة المقطع بجودة عالية وصورة واضحة كاملة، بالإضافة للبث المباشر لكل المباريات بدون تقطيع، "
        f"تفضل بزيارة موقعنا الآن:\n🔗 {WEBSITE_URL}\n"
        f"ولا تنسَ الاشتراك في تليجرام ليصلك كل جديد: {TELEGRAM_GROUP_URL}"
    )
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"Uploading highlight video to Facebook for match {match_id}...")
    try:
        fb_vid_id = post_fb_video(desc, video_to_upload_fb)
        if fb_vid_id:
            fb_url = f"https://www.facebook.com/watch/?v={fb_vid_id}"
            cursor.execute("INSERT INTO match_highlights (match_id, platform, video_url) VALUES (?, ?, ?)", (match_id, "facebook", fb_url))
            conn.commit()
            post_fb_comment(fb_vid_id, comment_text)
    except Exception as e:
        print(f"Error uploading to Facebook: {e}")

    # Process for YouTube (PiP Evasion)
    print("Processing video for YouTube...")
    temp_yt_shorts = f"/tmp/{match_id}_yt_shorts.mp4"
    yt_success = process_video_for_shorts(temp_file, temp_yt_shorts, title=title_text, platform="youtube")
    
    if yt_success:
        try:
            print("Attempting automatic upload to YouTube Shorts...")
            yt_title = f"أهداف مباراة {team_a} ضد {team_b} 🔥 #Shorts #يلا_شوت"
            yt_vid_id = yt_upload(temp_yt_shorts, yt_title, desc)
            if yt_vid_id:
                yt_url = f"https://youtu.be/{yt_vid_id}"
                cursor.execute("INSERT INTO match_highlights (match_id, platform, video_url) VALUES (?, ?, ?)", (match_id, "youtube", yt_url))
                conn.commit()
        except Exception as yt_err:
            print(f"YouTube Shorts auto-upload skipped or error: {yt_err}")

    conn.close()

    # Cleanup
    for p in [temp_file, temp_fb_shorts, temp_yt_shorts]:
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
