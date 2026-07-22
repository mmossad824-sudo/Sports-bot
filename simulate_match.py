import sqlite3
import os
import time
from datetime import datetime, timedelta
import sys

# Add directory to path to import local modules
sys.path.append(os.path.dirname(__file__))

import scraper
import bot

DB_PATH = os.path.join(os.path.dirname(__file__), "matches.db")

def simulate_match():
    print("=== بدء محاكاة مباراة إسبانيا والأرجنتين ===")
    
    # 1. تهيئة قاعدة البيانات وإدخال المباراة كـ "لم تبدأ"
    scraper.init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    match_id = "test_spain_argentina_2026"
    cairo_now = datetime.utcnow() + timedelta(hours=3)
    cairo_today = cairo_now.strftime("%Y-%m-%d")
    
    start_time = (cairo_now + timedelta(minutes=15)).strftime("%H:%M") # Starts in 15 mins
    
    # Insert or replace
    cursor.execute("DELETE FROM matches WHERE id = ?", (match_id,))
    cursor.execute("""
        INSERT INTO matches 
        (id, tournament, teamA, teamB, scoreA, scoreB, time, status, channel, round, logoA, logoB, link, stream_type, stream_url, match_date, updated_at, telegram_start_sent, telegram_half_sent, telegram_end_sent, last_telegram_scoreA, last_telegram_scoreB, mid_match_clip_uploaded)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?, 0)
    """, (
        match_id, "كأس العالم 2026", "إسبانيا", "الأرجنتين", "-", "-", start_time, "لم تبدأ", "beIN Sports", "النهائي", "", "", "https://www.yallakora.com/match-center/", None, None, cairo_today, cairo_now.isoformat(), "0", "0"
    ))
    conn.commit()
    
    print(f"[1] تم إدخال المباراة. التوقيت: {start_time} - الحالة: لم تبدأ")
    
    # 2. محاكاة فحص الإشعارات (المباراة تبدأ بعد 15 دقيقة، يجب أن يرسل إشعار البداية)
    print("\n[2] فحص التنبيهات الأول (تنبيه ما قبل المباراة)...")
    bot.check_and_send_alerts()
    
    # 3. تحديث حالة المباراة إلى "جارية الآن"
    print("\n[3] تحديث حالة المباراة إلى 'جارية الآن'...")
    cursor.execute("UPDATE matches SET status = 'جارية الآن', scoreA = '0', scoreB = '0', last_telegram_scoreA = '0', last_telegram_scoreB = '0' WHERE id = ?", (match_id,))
    conn.commit()
    bot.check_and_send_alerts() # Nothing should happen if no goals
    
    # 4. محاكاة هدف لإسبانيا
    print("\n[4] إسبانيا تسجل هدفاً! (النتيجة 1-0)...")
    cursor.execute("UPDATE matches SET scoreA = '1' WHERE id = ?", (match_id,))
    conn.commit()
    bot.check_and_send_alerts() # Should trigger goal alert for Spain
    
    # 5. تشغيل صياد الأهداف (جلب فيديو الهدف)
    print("\n[5] تشغيل صياد الأهداف (Mid-match Clips)...")
    scraper.catch_live_goals()
    
    # 6. محاكاة نهاية الشوط الأول
    print("\n[6] إعلان نهاية الشوط الأول...")
    cursor.execute("UPDATE matches SET status = 'بين الشوطين' WHERE id = ?", (match_id,))
    conn.commit()
    bot.check_and_send_alerts() # Should trigger halftime alert
    
    # 7. الشوط الثاني وهدف للأرجنتين
    print("\n[7] الأرجنتين تتعادل! (النتيجة 1-1)...")
    cursor.execute("UPDATE matches SET status = 'جارية الآن', scoreB = '1' WHERE id = ?", (match_id,))
    conn.commit()
    bot.check_and_send_alerts() # Should trigger goal alert for Argentina
    
    # 8. نهاية المباراة
    print("\n[8] إعلان نهاية المباراة! (1-1)...")
    cursor.execute("UPDATE matches SET status = 'انتهت' WHERE id = ?", (match_id,))
    conn.commit()
    bot.check_and_send_alerts() # Should trigger end alert
    
    conn.close()
    print("\n=== تمت المحاكاة بنجاح ===")

if __name__ == "__main__":
    simulate_match()
