import sys
import os
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from youtube_uploader import get_access_token
import requests

def delete_all_upcoming_broadcasts():
    token = get_access_token()
    if not token:
        print("Failed to get YouTube access token.")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    print("Fetching upcoming broadcasts...")
    url = "https://www.googleapis.com/youtube/v3/liveBroadcasts?part=id,snippet&broadcastStatus=upcoming&broadcastType=all"
    
    deleted_count = 0
    while url:
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            print(f"Error fetching broadcasts: {r.text}")
            break
            
        data = r.json()
        items = data.get("items", [])
        
        for item in items:
            broadcast_id = item["id"]
            title = item["snippet"]["title"]
            print(f"Deleting broadcast '{title}' (ID: {broadcast_id})...")
            
            del_url = f"https://www.googleapis.com/youtube/v3/liveBroadcasts?id={broadcast_id}"
            del_r = requests.delete(del_url, headers=headers)
            
            if del_r.status_code == 204:
                print(f"✅ Successfully deleted {broadcast_id}")
                deleted_count += 1
            else:
                print(f"❌ Failed to delete {broadcast_id}: {del_r.text}")
                
        next_page = data.get("nextPageToken")
        if next_page:
            url = f"https://www.googleapis.com/youtube/v3/liveBroadcasts?part=id,snippet&broadcastStatus=upcoming&broadcastType=all&pageToken={next_page}"
        else:
            url = None
            
    print(f"Done! Deleted {deleted_count} ghost broadcasts.")

if __name__ == "__main__":
    delete_all_upcoming_broadcasts()
