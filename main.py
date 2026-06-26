from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
import sqlite3
import os
from datetime import datetime
from scraper import scrape_yallakora, update_live_streams, init_db, DB_PATH
from bot import broadcast_schedule, check_and_send_alerts
from zoneinfo import ZoneInfo

app = FastAPI(title="Sports Bot API", description="Automated Sports scraping and streaming backend")

# Enable CORS for all domains so Vercel frontend can call it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    scrape_three_days()
    # Broadcast daily matches list to Telegram
    try:
        broadcast_schedule()
    except Exception as e:
        print(f"Error broadcasting schedule: {e}")

def job_stream_update():
    print(f"[{datetime.now().isoformat()}] Starting scheduled scraping and stream link update...")
    try:
        from datetime import timedelta
        cairo_now = datetime.utcnow() + timedelta(hours=3)
        for offset in [0, 1]:
            d = cairo_now + timedelta(days=offset)
            date_str = f"{d.month}/{d.day}/{d.year}"
            scrape_yallakora(date_str)
    except Exception as e:
        print(f"Error scraping Yallakora during stream update: {e}")
    try:
        update_live_streams()
    except Exception as e:
        print(f"Error updating stream links: {e}")
    try:
        check_and_send_alerts()
    except Exception as e:
        print(f"Error checking and sending Telegram alerts: {e}")

@app.on_event("startup")
def startup_event():
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
        
    # Run initial scrape and stream update on startup so database is never empty
    print("Running startup scraping tasks...")
    scrape_three_days()
    update_live_streams()
    
    # Run initial Telegram alerts check
    try:
        check_and_send_alerts()
    except Exception as e:
        print(f"Error checking Telegram alerts on startup: {e}")
        
    # Broadcast to Telegram on startup for testing/initialization
    try:
        print("Sending initial Telegram schedule broadcast...")
        broadcast_schedule()
    except Exception as e:
        print(f"Error broadcasting on startup: {e}")
    
    # Schedule Morning Scrape: Every day at 05:00 AM Cairo time
    scheduler.add_job(job_morning_scrape, 'cron', hour=5, minute=0)
    # Schedule Noon Broadcast: Every day at 12:00 PM (noon) Cairo time
    scheduler.add_job(broadcast_schedule, 'cron', hour=12, minute=0)
    # Schedule Stream Link Updater: Every 3 minutes
    scheduler.add_job(job_stream_update, 'interval', minutes=3)
    
    scheduler.start()
    print("Scheduler started successfully.")

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
    print("Scheduler stopped.")

@app.get("/")
def read_root():
    return {
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "database_exists": os.path.exists(DB_PATH)
    }

@app.get("/api/matches")
def get_matches():
    if not os.path.exists(DB_PATH):
        return []
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM matches")
    rows = cursor.fetchall()
    conn.close()
    
    matches = []
    for r in rows:
        matches.append(dict(r))
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
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Match not found")
        
    return dict(row)

@app.post("/api/scrape")
def trigger_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(job_morning_scrape)
    return {"message": "Scraping task started in the background."}

@app.post("/api/update-streams")
def trigger_stream_update(background_tasks: BackgroundTasks):
    background_tasks.add_task(job_stream_update)
    return {"message": "Stream updating task started in the background."}

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

if __name__ == "__main__":
    import uvicorn
    # Read port from environment (Hugging Face default is 7860)
    port = int(os.getenv("PORT", 7860))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
