from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager
import sqlite3
import os
from datetime import datetime
from scraper import scrape_yallakora, update_live_streams, init_db, DB_PATH, cleanup_old_data
from bot import broadcast_schedule, check_and_send_alerts
from zoneinfo import ZoneInfo

try:
    cairo_tz = ZoneInfo("Africa/Cairo")
    scheduler = BackgroundScheduler(timezone=cairo_tz)
    print("Scheduler initialized with Africa/Cairo timezone.")
except Exception as e:
    scheduler = BackgroundScheduler()
    print(f"Scheduler initialized with default timezone. Error: {e}")

def scrape_three_days():
    from datetime import timedelta
    cairo_now = datetime.utcnow() + timedelta(hours=3)
    for offset in [-1, 0, 1]:
        d = cairo_now + timedelta(days=offset)
        date_str = f"{d.month}/{d.day}/{d.year}"
        try:
            scrape_yallakora(date_str)
        except Exception as e:
            print(f"Error scraping date {date_str}: {e}")

# Background Jobs wrapper
def job_morning_scrape():
    print(f"[{datetime.now().isoformat()}] Starting scheduled morning scrape...")
    cleanup_old_data()
    scrape_three_days()
    try:
        broadcast_schedule()
    except Exception as e:
        print(f"Error broadcasting schedule: {e}")

def job_stream_update():
    print(f"[{datetime.now().isoformat()}] Starting scheduled scraping, stream link update, and highlights update...")
    try:
        from datetime import timedelta
        cairo_now = datetime.utcnow() + timedelta(hours=3)
        d = cairo_now
        date_str = f"{d.month}/{d.day}/{d.year}"
        scrape_yallakora(date_str)
    except Exception as e:
        print(f"Error scraping Yallakora during stream update: {e}")
    try:
        update_live_streams()
    except Exception as e:
        print(f"Error updating stream links: {e}")
    try:
        from scraper import update_finished_matches_highlights, catch_live_goals
        update_finished_matches_highlights()
        catch_live_goals()
    except Exception as e:
        print(f"Error updating finished match highlights or catching live goals: {e}")
    try:
        check_and_send_alerts()
    except Exception as e:
        print(f"Error checking and sending Telegram alerts: {e}")


def job_auto_live_stream():
    """Scheduled job to auto-manage the YouTube live stream."""
    try:
        from live_manager import auto_manage_live_streams
        auto_manage_live_streams()
    except Exception as e:
        print(f"[AutoLive] Error in auto_manage_live_streams: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    
    # Clean up old Moroccan League matches from database
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM matches WHERE tournament LIKE '%المغربي%' OR tournament LIKE '%العرش%'")
        conn.commit()
        conn.close()
        print("Database cleaned up (Moroccan League matches deleted).")
    except Exception as e:
        print(f"Error cleaning database: {e}")
        
    # Run initial scrape and stream update on startup
    print("Running startup scraping tasks...")
    scrape_three_days()
    update_live_streams()
    try:
        from scraper import update_finished_matches_highlights
        update_finished_matches_highlights()
    except Exception as e:
        print(f"Error updating finished match highlights on startup: {e}")
    
    try:
        check_and_send_alerts()
    except Exception as e:
        print(f"Error checking Telegram alerts on startup: {e}")
        
    try:
        print("Sending initial Telegram schedule broadcast...")
        broadcast_schedule()
    except Exception as e:
        print(f"Error broadcasting on startup: {e}")
    
    # Schedule Morning Scrape: Every day at 05:00 AM Cairo time
    scheduler.add_job(job_morning_scrape, 'cron', hour=5, minute=0)
    # Schedule Noon Broadcast: Every day at 12:00 PM (noon) Cairo time
    scheduler.add_job(broadcast_schedule, 'cron', hour=12, minute=0)
    # Schedule Stream Link Updater (real streams for all matches): Every 1 minute
    scheduler.add_job(job_stream_update, 'interval', minutes=1)
    # Schedule Auto YouTube Live Stream Orchestrator: Every 5 minutes
    scheduler.add_job(job_auto_live_stream, 'interval', minutes=5, id='auto_yt_live')
    
    scheduler.start()
    print("Scheduler started successfully.")
    
    yield
    
    scheduler.shutdown()
    print("Scheduler stopped.")

app = FastAPI(
    title="Sports Bot API",
    description="Automated Sports scraping and streaming backend",
    lifespan=lifespan
)

# Enable CORS for all domains so Vercel frontend can call it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "database_exists": os.path.exists(DB_PATH)
    }

# ── Admin Endpoints (للتحكم اليدوي في البث من السحابة) ──────────────────────

@app.post("/api/admin/trigger_test_stream")
def trigger_test_stream(background_tasks: BackgroundTasks):
    """تشغيل بث يوتيوب تجريبي من السيرفر السحابي للتحقق من عمله."""
    def _run():
        try:
            from live_manager import start_stream, watch_loop, is_stream_alive, increment_todays_yt_count
            import threading
            if is_stream_alive():
                print("[TestStream] Already running.")
                return
            meta = start_stream(
                team_a="ريال مدريد",
                team_b="برشلونة",
                score="0 - 0",
                logo_a_url="https://crests.football-data.org/86.png",
                logo_b_url="https://crests.football-data.org/81.png",
                match_id="test"
            )
            if meta:
                increment_todays_yt_count()
                threading.Thread(target=watch_loop, daemon=True).start()
                print(f"[TestStream] Live at {meta['watch_url']}")
        except Exception as e:
            print(f"[TestStream] Error: {e}")
    background_tasks.add_task(_run)
    return {"status": "starting", "message": "Test stream triggered on cloud. Check YouTube in ~30 seconds."}


@app.post("/api/admin/stop_stream")
def stop_stream_endpoint():
    """إيقاف أي بث يوتيوب يعمل حالياً على السيرفر."""
    try:
        from live_manager import stop_stream
        stop_stream()
        return {"status": "stopped"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/admin/stream_status")
def stream_status():
    """التحقق من حالة البث التفاعلي الحالي."""
    try:
        from live_manager import is_stream_alive, META_FILE, count_todays_yt_streams, MAX_YT_STREAMS_PER_DAY
        import json as _json
        alive = is_stream_alive()
        meta = {}
        if alive and os.path.exists(META_FILE):
            meta = _json.load(open(META_FILE))
        return {
            "alive": alive,
            "today_streams": count_todays_yt_streams(),
            "daily_limit": MAX_YT_STREAMS_PER_DAY,
            "meta": meta
        }
    except Exception as e:
        return {"alive": False, "error": str(e)}


@app.get("/api/matches")
def get_matches():
    if not os.path.exists(DB_PATH):
        return []
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM matches")
    rows = cursor.fetchall()
    
    try:
        cursor.execute("SELECT * FROM match_highlights")
        hl_rows = cursor.fetchall()
        highlights_by_match = {}
        for hl in hl_rows:
            hl_dict = dict(hl)
            m_id = hl_dict["match_id"]
            if m_id not in highlights_by_match:
                highlights_by_match[m_id] = []
            highlights_by_match[m_id].append(hl_dict)
    except sqlite3.OperationalError:
        highlights_by_match = {}

    conn.close()
    
    matches = []
    for r in rows:
        m_dict = dict(r)
        m_dict["highlights"] = highlights_by_match.get(m_dict["id"], [])
        matches.append(m_dict)
    return matches

@app.get("/api/matches/{match_id}")
def get_match_detail(match_id: str):
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Database not found")
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM matches WHERE id = ?", (match_id,))
    row = cursor.fetchone()
    
    try:
        cursor.execute("SELECT * FROM match_highlights WHERE match_id = ?", (match_id,))
        hl_rows = cursor.fetchall()
        highlights = [dict(hl) for hl in hl_rows]
    except sqlite3.OperationalError:
        highlights = []
        
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Match not found")
        
    match_dict = dict(row)
    match_dict["highlights"] = highlights
    return match_dict

@app.post("/api/scrape")
def trigger_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(job_morning_scrape)
    return {"message": "Scraping task started in the background."}

@app.get("/api/update_streams")
def trigger_stream_update():
    """Manual trigger to update streams immediately"""
    job_stream_update()
    return {"status": "Stream update triggered"}

@app.get("/api/test_live_stream")
def test_live_stream_cloud(bg_tasks: BackgroundTasks):
    """Manual trigger to start a test live stream on the cloud server for testing stability"""
    from live_manager import start_stream
    def run_test():
        start_stream(
            team_a="ريال مدريد", 
            team_b="برشلونة", 
            score="0 - 0",
            match_id="test_cloud_001",
            real_match_link=f"https://{os.getenv('WEBSITE_URL', 'yalla-shoot-today.vercel.app')}"
        )
    bg_tasks.add_task(run_test)
    return {"status": "Test live stream launched in the background on the cloud server!"}

@app.get("/api/check_ports")
def check_ports():
    import socket
    results = {}
    for port in [1935, 443, 80]:
        try:
            sock = socket.create_connection(("a.rtmp.youtube.com", port), timeout=3)
            results[port] = "OPEN"
            sock.close()
        except Exception as e:
            results[port] = f"CLOSED or ERROR: {str(e)}"
        
        try:
            sock = socket.create_connection(("a.rtmps.youtube.com", port), timeout=3)
            results[f"rtmps_{port}"] = "OPEN"
            sock.close()
        except Exception as e:
            results[f"rtmps_{port}"] = f"CLOSED or ERROR: {str(e)}"
    return results

@app.post("/api/matches/{match_id}/update")
def update_match(match_id: str, data: dict):
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Database not found")
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    # Accept fields to update dynamically
    fields = ["status", "scoreA", "scoreB", "stream_url", "stream_type", "channel", "round"]
    for field in fields:
        if field in data:
            updates.append(f"{field} = ?")
            params.append(data[field])
            
    if not updates:
        conn.close()
        return {"message": "No fields to update"}
        
    updates.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    
    params.append(match_id)
    query = f"UPDATE matches SET {', '.join(updates)} WHERE id = ?"
    
    cursor.execute(query, params)
    conn.commit()
    conn.close()
    return {"message": f"Match {match_id} updated successfully"}

@app.get("/api/proxy")
def proxy_iframe(url: str):
    from fastapi.responses import HTMLResponse
    from bs4 import BeautifulSoup
    import requests
    import urllib.parse
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Referer': url
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return HTMLResponse(
                content=f"<div style='color: white; text-align: center; padding: 20px; font-family: sans-serif;'><h3>خطأ في تحميل سيرفر البث (كود: {response.status_code})</h3></div>", 
                status_code=response.status_code
            )
            
        # Parse HTML and inject <base href="...">
        soup = BeautifulSoup(response.content, 'html.parser')
        
        parsed = urllib.parse.urlparse(url)
        base_dir = os.path.dirname(parsed.path)
        base_url = f"{parsed.scheme}://{parsed.netloc}{base_dir}"
        if not base_url.endswith('/'):
            base_url += '/'
            
        head = soup.find('head')
        if not head:
            head = soup.new_tag('head')
            if soup.html:
                soup.html.insert(0, head)
            else:
                soup.insert(0, head)
                
        base_tag = soup.find('base')
        if base_tag:
            base_tag['href'] = base_url
        else:
            new_base = soup.new_tag('base', href=base_url)
            head.insert(0, new_base)
            
        # Inject referrer policy to bypass HLS hotlinking check
        new_meta = soup.new_tag('meta', name='referrer', content='no-referrer')
        head.insert(0, new_meta)
        
        # Strip X-Frame-Options and CSP headers that block embedding
        headers_to_send = {
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Content-Type": "text/html; charset=utf-8"
            # Intentionally NOT forwarding X-Frame-Options or Content-Security-Policy
        }
        
        return HTMLResponse(content=str(soup), headers=headers_to_send)
        
    except Exception as e:
        return HTMLResponse(
            content=f"<div style='color: white; text-align: center; padding: 20px; font-family: sans-serif;'><h3>حدث خطأ أثناء الاتصال بسيرفر البث الوسيط: {str(e)}</h3></div>", 
            status_code=500
        )

@app.get("/api/news")
def get_all_news():
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, source, link, pub_date, image_url, created_at FROM news ORDER BY pub_date DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/api/news/{news_id}")
def get_news(news_id: str):
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Database not found")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM news WHERE id = ?", (news_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    raise HTTPException(status_code=404, detail="News not found")

@app.post("/api/news")
def add_news(data: dict):
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Database not found")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO news 
        (id, title, content, source, link, pub_date, image_url, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("id"),
        data.get("title"),
        data.get("content"),
        data.get("source"),
        data.get("link"),
        data.get("pub_date"),
        data.get("image_url", ""),
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()
    return {"message": "News added successfully"}


if __name__ == "__main__":
    import uvicorn
    # Read port from environment (Hugging Face default is 7860)
    port = int(os.getenv("PORT", 7860))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
