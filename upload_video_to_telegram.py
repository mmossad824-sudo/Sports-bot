import os
import sys
import subprocess
import requests
import sqlite3
import json

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@yalla_shoottoday")
DB_PATH = os.path.join(os.path.dirname(__file__), "matches.db")

def upload_video(match_id, team_a, team_b, video_url):
    if not BOT_TOKEN:
        print("BOT_TOKEN is missing")
        return
        
    print(f"Downloading video from {video_url}...")
    temp_file = f"/tmp/{match_id}.mp4"
    
    # Download the best quality mp4
    try:
        subprocess.run(["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", "-o", temp_file, video_url], check=True)
    except Exception as e:
        print(f"Failed to download video: {e}")
        return
        
    if not os.path.exists(temp_file):
        print("Video file not found after download.")
        return
        
    print(f"Uploading video to Telegram for match {match_id}...")
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
        caption = f"🎬 ملخص وأهداف مباراة {team_a} ضد {team_b}"
        
        with open(temp_file, 'rb') as video_file:
            files = {'video': video_file}
            data = {'chat_id': CHANNEL_ID, 'caption': caption}
            response = requests.post(url, data=data, files=files, timeout=600)
            
        if response.status_code == 200:
            res_data = response.json()
            message_id = res_data.get('result', {}).get('message_id')
            if message_id:
                # Assuming channel username is @yalla_shoottoday, remove @
                channel_username = CHANNEL_ID.replace('@', '')
                embed_url = f"https://t.me/{channel_username}/{message_id}?embed=1&mode=tme"
                print(f"Uploaded successfully. Embed URL: {embed_url}")
                
                # Update DB
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("UPDATE matches SET telegram_embed_url = ? WHERE id = ?", (embed_url, match_id))
                
                # Also prepend this to stream_url sources
                cursor.execute("SELECT stream_url FROM matches WHERE id = ?", (match_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    try:
                        sources = json.loads(row[0])
                        # Check if telegram is already there
                        if not any(s.get('type') == 'telegram' for s in sources):
                            sources.insert(0, {
                                "name": "سيرفر تليجرام (سريع وبدون حظر)",
                                "type": "telegram",
                                "url": embed_url
                            })
                            cursor.execute("UPDATE matches SET stream_url = ? WHERE id = ?", (json.dumps(sources), match_id))
                    except:
                        pass
                conn.commit()
                conn.close()
        else:
            print(f"Failed to upload to Telegram: {response.text}")
    except Exception as e:
        print(f"Error uploading video: {e}")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python upload_video_to_telegram.py <match_id> <team_a> <team_b> <video_url>")
        sys.exit(1)
    upload_video(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
