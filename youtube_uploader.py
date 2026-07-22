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


def upload_video(video_path: str, title: str, description: str, tags: list = None) -> bool:
    """رفع فيديو مباشر إلى القناة عبر YouTube Data API Resumable Upload"""
    access_token = get_access_token()
    if not access_token:
        return False

    if not os.path.exists(video_path):
        logger.error(f"ملف الفيديو غير موجود: {video_path}")
        return False

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
            return False

        resumable_url = init_res.headers.get("Location")
        if not resumable_url:
            logger.error("لم يتم استلام رابط الرفع من يوتيوب.")
            return False

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
            return True
        else:
            logger.error(f"فشل رفع ملف الفيديو: {upload_res.text}")
            return False

    except Exception as e:
        logger.error(f"حدث استثناء أثناء رفع الفيديو ليوتيوب: {e}")
        return False


if __name__ == "__main__":
    logger.info("اختبار فحص مكتبة أتمتة يوتيوب...")
