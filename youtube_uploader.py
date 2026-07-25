"""
youtube_uploader.py — سكريبت أتمتة يوتيوب لرفع الفيديوهات القصيرة (Shorts) وإصدار البثوث
"""
import os
import json
import logging
import requests
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ─── الإعدادات ────────────────────────────────────────────────────────────────
CLIENT_ID     = os.getenv("YOUTUBE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")
REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN", "")

TOKEN_URI = "https://oauth2.googleapis.com/token"


def get_access_token() -> str | None:
    """الحصول على Access Token متجدد باستخدام Refresh Token"""
    if not CLIENT_ID or not CLIENT_SECRET or not REFRESH_TOKEN:
        logger.warning("مفاتيح YouTube OAuth غير مكتملة.")
        return None

    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }

    try:
        r = requests.post(TOKEN_URI, data=payload, timeout=20)
        data = r.json()
        if r.status_code == 200 and "access_token" in data:
            logger.info("✅ تم الحصول على Access Token جديد من يوتيوب")
            return data["access_token"]
        else:
            logger.error(f"خطأ في تجديد التوكن: {r.text}")
            return None
    except Exception as e:
        logger.error(f"استثناء أثناء تجديد توكن يوتيوب: {e}")
        return None


def post_youtube_comment(video_id: str, message: str) -> bool:
    """Post a top-level comment on a YouTube video."""
    access_token = get_access_token()
    if not access_token:
        return False
    
    url = "https://www.googleapis.com/youtube/v3/commentThreads?part=snippet"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8"
    }
    payload = {
        "snippet": {
            "videoId": video_id,
            "topLevelComment": {
                "snippet": {
                    "textOriginal": message
                }
            }
        }
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        data = r.json()
        if r.status_code == 200 and data.get("id"):
            logger.info(f"✅ YT Comment posted on video {video_id}")
            return True
        else:
            logger.error(f"YT Comment failed: {r.status_code} — {r.text[:300]}")
            return False
    except Exception as e:
        logger.error(f"YT Comment exception: {e}")
        return False


def upload_video(video_path: str, title: str, description: str, tags: list = None) -> str:
    """رفع فيديو مباشر إلى القناة عبر YouTube Data API Resumable Upload. Returns video_id."""
    access_token = get_access_token()
    if not access_token:
        return None

    if not os.path.exists(video_path):
        logger.error(f"ملف الفيديو غير موجود: {video_path}")
        return None

    upload_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/mp4",
        "X-Upload-Content-Length": str(os.path.getsize(video_path))
    }

    snippet = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags or ["يلا_شوت", "بث_مباشر", "مباريات_اليوم", "Football", "Shorts"],
            "categoryId": "17"  # Sports
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    try:
        # 1. Initiate Upload Session
        init_res = requests.post(upload_url, headers=headers, data=json.dumps(snippet), timeout=30)
        if init_res.status_code != 200:
            logger.error(f"فشل إنشاء جلسة الرفع على يوتيوب: {init_res.text}")
            return None

        resumable_url = init_res.headers.get("Location")
        if not resumable_url:
            logger.error("لم يتم استلام رابط الرفع من يوتيوب.")
            return None

        # 2. Upload Video Binary Bytes
        with open(video_path, "rb") as f:
            upload_res = requests.put(
                resumable_url,
                headers={"Content-Type": "video/mp4"},
                data=f,
                timeout=180
            )

        if upload_res.status_code in (200, 201):
            video_data = upload_res.json()
            video_id = video_data.get("id")
            logger.info(f"🎉 تم رفع الفيديو بنجاح على قناتك في يوتيوب! رابط الفيديو: https://youtu.be/{video_id}")
            return video_id
        else:
            logger.error(f"فشل رفع ملف الفيديو: {upload_res.text}")
            return None

    except Exception as e:
        logger.error(f"حدث استثناء أثناء رفع الفيديو ليوتيوب: {e}")
        return None

def create_youtube_live(title: str, description: str, scheduled_start_time: str = None) -> dict | None:
    """
    Create a YouTube Live Broadcast and bind it to a stream.
    Returns dict with {broadcast_id, stream_id, stream_key, rtmp_url, watch_url} or None on failure.
    scheduled_start_time: ISO 8601 string e.g. '2026-07-24T22:00:00+03:00'. If None, starts immediately.
    """
    access_token = get_access_token()
    if not access_token:
        return None

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8"
    }

    # 1. Create Broadcast
    broadcast_url = "https://www.googleapis.com/youtube/v3/liveBroadcasts?part=snippet,status,contentDetails"
    now_utc = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
    start_time = scheduled_start_time or now_utc
    broadcast_body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "scheduledStartTime": start_time
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        },
        "contentDetails": {
            "enableAutoStart": True,
            "enableAutoStop": True,
            "enableDvr": True,
            "recordFromStart": True,
            "startWithSlate": False
        }
    }

    try:
        r = requests.post(broadcast_url, headers=headers, json=broadcast_body, timeout=30)
        bc_data = r.json()
        if r.status_code not in (200, 201) or "id" not in bc_data:
            logger.error(f"Failed to create broadcast: {r.text[:300]}")
            return None
        broadcast_id = bc_data["id"]
        logger.info(f"✅ YouTube Broadcast created: {broadcast_id}")

        # 2. Create Stream
        stream_url = "https://www.googleapis.com/youtube/v3/liveStreams?part=snippet,cdn"
        stream_body = {
            "snippet": {"title": title[:100]},
            "cdn": {
                "frameRate": "30fps",
                "ingestionType": "rtmp",
                "resolution": "1080p"
            }
        }
        r2 = requests.post(stream_url, headers=headers, json=stream_body, timeout=30)
        st_data = r2.json()
        if r2.status_code not in (200, 201) or "id" not in st_data:
            logger.error(f"Failed to create stream: {r2.text[:300]}")
            return None
        stream_id = st_data["id"]
        ingestion = st_data["cdn"]["ingestionInfo"]
        rtmp_url = ingestion["ingestionAddress"]
        stream_key = ingestion["streamName"]
        logger.info(f"✅ YouTube Stream created: {stream_id} | RTMP: {rtmp_url}")

        # 3. Bind broadcast to stream
        bind_url = f"https://www.googleapis.com/youtube/v3/liveBroadcasts/bind?id={broadcast_id}&part=id,contentDetails&streamId={stream_id}"
        r3 = requests.post(bind_url, headers=headers, json={}, timeout=30)
        if r3.status_code != 200:
            logger.error(f"Failed to bind broadcast: {r3.text[:200]}")
        else:
            logger.info(f"✅ Broadcast bound to stream successfully")

        watch_url = f"https://www.youtube.com/watch?v={broadcast_id}"
        return {
            "broadcast_id": broadcast_id,
            "stream_id": stream_id,
            "stream_key": stream_key,
            "rtmp_url": rtmp_url,
            "rtmp_full": f"{rtmp_url}/{stream_key}",
            "watch_url": watch_url
        }

    except Exception as e:
        logger.error(f"Exception creating YouTube live: {e}")
        return None


def transition_broadcast(broadcast_id: str, status: str, access_token: str) -> bool:
    """Transition a YouTube broadcast to testing or live."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    url = (f"https://www.googleapis.com/youtube/v3/liveBroadcasts/transition"
           f"?broadcastStatus={status}&id={broadcast_id}&part=id,status")
    try:
        r = requests.post(url, headers=headers, json={}, timeout=20)
        if r.status_code == 200:
            logger.info(f"✅ Broadcast transitioned to '{status}'")
            return True
        else:
            logger.warning(f"Transition to '{status}' returned {r.status_code}: {r.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Transition exception: {e}")
        return False


def end_youtube_live(broadcast_id: str) -> bool:
    """Transition a YouTube Live Broadcast to 'complete' state."""
    access_token = get_access_token()
    if not access_token or not broadcast_id:
        return False
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    url = f"https://www.googleapis.com/youtube/v3/liveBroadcasts/transition?broadcastStatus=complete&id={broadcast_id}&part=id,status"
    try:
        r = requests.post(url, headers=headers, json={}, timeout=20)
        if r.status_code == 200:
            logger.info(f"✅ YouTube Live {broadcast_id} ended.")
            return True
        else:
            logger.error(f"Failed to end YouTube live: {r.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Exception ending YouTube live: {e}")
        return False


# Alias for backward compatibility with test_youtube.yml and other callers
def upload_to_youtube_shorts(video_path: str, title: str, description: str, tags: list = None) -> str:
    """Alias for upload_video — uploads a Short/video to YouTube."""
    return upload_video(video_path, title, description, tags)


if __name__ == "__main__":
    logger.info("اختبار فحص مكتبة أتمتة يوتيوب...")

