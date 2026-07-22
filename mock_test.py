import sqlite3
import os
import time
from datetime import datetime, timedelta
import sys

# Add directory to path to import local modules
sys.path.append(os.path.dirname(__file__))

import scraper
import bot

# 1. Override the tokens and sending functions to show the exact output instead of skipping
bot.BOT_TOKEN = "MOCK_TOKEN"
bot.CHANNEL_ID = "MOCK_CHANNEL"
bot.FB_PAGE_TOKEN = "MOCK_FB_TOKEN"
bot.FB_PAGE_ID = "MOCK_FB_ID"

# Save the original functions
original_send_telegram = bot.send_telegram_api
original_requests_post = bot.requests.post

def mock_send_telegram(method, payload):
    print("\n" + "="*50)
    print("📱 [رسالة تليجرام جديدة تم إرسالها بنجاح!]")
    if "text" in payload:
        print(payload["text"])
    elif "question" in payload:
        print(f"📊 [استطلاع رأي]: {payload['question']}")
        print(f"خيارات: {payload['options']}")
    print("="*50 + "\n")
    return {"ok": True, "result": {"message_id": 999}}

def mock_requests_post(url, data=None, json=None, **kwargs):
    if "graph.facebook.com" in url:
        print("\n" + "="*50)
        print("📘 [منشور فيسبوك جديد تم نشره بنجاح!]")
        if data and "message" in data:
            print(data["message"])
        print("="*50 + "\n")
    class MockResponse:
        status_code = 200
        def json(self): return {"id": "12345"}
    return MockResponse()

# Apply the overrides
bot.send_telegram_api = mock_send_telegram
bot.requests.post = mock_requests_post


DB_PATH = os.path.join(os.path.dirname(__file__), "matches.db")

def simulate_real_test():
    print("🚀 === بدء الاختبار الحقيقي للنظام (بدون مفاتيح) === 🚀\n")
    
    scraper.init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    match_id = "real_test_match_123"
    cairo_now = datetime.utcnow() + timedelta(hours=3)
    cairo_today = cairo_now.strftime("%Y-%m-%d")
    start_time = (cairo_now + timedelta(minutes=10)).strftime("%H:%M")
    
    cursor.execute("DELETE FROM matches WHERE id = ?", (match_id,))
    cursor.execute("""
        INSERT INTO matches 
        (id, tournament, teamA, teamB, scoreA, scoreB, time, status, channel, round, logoA, logoB, link, stream_type, stream_url, match_date, updated_at, telegram_start_sent, telegram_half_sent, telegram_end_sent, last_telegram_scoreA, last_telegram_scoreB, mid_match_clip_uploaded)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?, 0)
    """, (
        match_id, "دوري أبطال أوروبا", "ريال مدريد", "بايرن ميونخ", "-", "-", start_time, "لم تبدأ", "beIN Sports", "نصف النهائي", "", "", "https://www.yallakora.com/match-center/", None, None, cairo_today, cairo_now.isoformat(), "0", "0"
    ))
    conn.commit()
    
    print("⏳ النظام ينتظر اقتراب المباراة...")
    bot.check_and_send_alerts() 
    
    print("\n🟢 الحكم يطلق صافرة البداية! (جارية الآن)")
    cursor.execute("UPDATE matches SET status = 'جارية الآن', scoreA = '0', scoreB = '0', last_telegram_scoreA = '0', last_telegram_scoreB = '0' WHERE id = ?", (match_id,))
    conn.commit()
    bot.check_and_send_alerts() 
    
    print("\n⚽ ريال مدريد يسجل الهدف الأول بقدم فينيسيوس!")
    # Here we mock the _get_scorer_name to return Vinicius just for the test
    bot._get_scorer_name = lambda m, h: "فينيسيوس جونيور" if h else ""
    cursor.execute("UPDATE matches SET scoreA = '1' WHERE id = ?", (match_id,))
    conn.commit()
    bot.check_and_send_alerts()
    
    print("\n🎥 صياد الأهداف التقط هدف فينيسيوس ويقوم بتحويله لفيديو Shorts لرفعه...")
    # Skip actual video processing to save time in console
    
    print("\n🏁 نهاية المباراة بفوز ريال مدريد 1-0")
    cursor.execute("UPDATE matches SET status = 'انتهت' WHERE id = ?", (match_id,))
    conn.commit()
    bot.check_and_send_alerts() 
    
    conn.close()
    print("\n✅ تمت محاكاة الاختبار الحي بنجاح وطباعة النتائج!")

if __name__ == "__main__":
    simulate_real_test()
