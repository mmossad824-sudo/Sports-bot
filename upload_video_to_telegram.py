import os
import sys
import subprocess
import requests
import sqlite3
import json
from video_processor import process_video_for_shorts

BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@yalla_shoot_today_Group")
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://yalla-shoot-today.vercel.app")
SPONSOR_URL = "https://www.profitablecpmrate.com/e4480b4a0a4ef0a7e842009f7c505039"
DB_PATH    = os.path.join(os.path.dirname(__file__), "matches.db")

def upload_video(match_id, team_a, team_b, video_url):
    if not BOT_TOKEN:
        print("BOT_TOKEN is missing")
        return
        
    print(f"Downloading video from {video_url}...")
    temp_file = f"/tmp/{match_id}.mp4"
    temp_shorts_file = f"/tmp/{match_id}_shorts.mp4"
    
    # Download the best quality mp4
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

    print(f"Uploading highlight video to Telegram for match {match_id}...")
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
        caption = (
            f"🎬 <b>ملخص وأهداف مباراة {team_a} ضد {team_b}</b>\n\n"
            f"⚡ جاهز للمشاركة على تيك توك وريلز الفيسبوك وShorts!\n\n"
            f"🔴 شاهد المزيد وتابع البث المباشر:\n{WEBSITE_URL}\n"
            f"🎁 اربح 130$ توقع المباراة التالية:\n{SPONSOR_URL}"
        )
        
        reply_markup = json.dumps({
            "inline_keyboard": [
                [{"text": "🔴 شاهد البث المباشر والأهداف HD", "url": WEBSITE_URL}],
                [{"text": "🎁 توقع وربح جوائز مادية", "url": SPONSOR_URL}]
            ]
        })

        with open(video_to_upload, 'rb') as video_file:
            files = {'video': video_file}
            data = {'chat_id': CHANNEL_ID, 'caption': caption, 'parse_mode': 'HTML', 'reply_markup': reply_markup}
            response = requests.post(url, data=data, files=files, timeout=600)
            
        if response.status_code == 200:
            res_data = response.json()
            message_id = res_data.get('result', {}).get('message_id')
            if message_id:
                channel_username = CHANNEL_ID.replace('@', '')
                embed_url = f"https://t.me/{channel_username}/{message_id}?embed=1&mode=tme"
                print(f"Uploaded successfully to Telegram. Embed URL: {embed_url}")
                
                # Update DB
                if os.path.exists(DB_PATH):
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE matches SET telegram_embed_url = ? WHERE id = ?", (embed_url, match_id))
                    
                    cursor.execute("SELECT stream_url FROM matches WHERE id = ?", (match_id,))
                    row = cursor.fetchone()
                    if row and row[0]:
                        try:
                            sources = json.loads(row[0])
                            if not any(s.get('type') == 'telegram' for s in sources):
                                sources.insert(0, {
                                    "name": "سيرفر تليجرام (سريع وبدون حظر)",
                                    "type": "telegram",
                                    "url": embed_url
                                })
                                cursor.execute("UPDATE matches SET stream_url = ? WHERE id = ?", (json.dumps(sources), match_id))
                        except Exception:
                            pass
                    conn.commit()
                    conn.close()

                # Also attempt YouTube Shorts upload if youtube_uploader is configured
                if shorts_success:
                    try:
                        from youtube_uploader import upload_video as yt_upload
                        print("Attempting automatic upload to YouTube Shorts...")
                        yt_title = f"أهداف مباراة {team_a} ضد {team_b} 🔥 #Shorts #يلا_شوت"
                        yt_desc = f"شاهد ملخص مباراة {team_a} و {team_b}\n\nلمتابعة البث المباشر:\n{WEBSITE_URL}"
                        yt_upload(temp_shorts_file, yt_title, yt_desc)
                    except Exception as yt_err:
                        print(f"YouTube Shorts auto-upload skipped or error: {yt_err}")
        else:
            print(f"Failed to upload to Telegram: {response.text}")
    except Exception as e:
        print(f"Error uploading video: {e}")
    finally:
        for p in [temp_file, temp_shorts_file]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python upload_video_to_telegram.py <match_id> <team_a> <team_b> <video_url>")
        sys.exit(1)
    upload_video(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
