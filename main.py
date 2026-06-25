from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
import sqlite3
import os
from datetime import datetime
from scraper import scrape_yallakora, update_live_streams, init_db, DB_PATH
from bot import broadcast_schedule

app = FastAPI(title="Sports Bot API", description="Automated Sports scraping and streaming backend")

# Enable CORS for all domains so Vercel frontend can call it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scheduler = BackgroundScheduler()

# Background Jobs wrapper
def job_morning_scrape():
    print(f"[{datetime.now().isoformat()}] Starting scheduled morning scrape...")
    scrape_yallakora()
    # Broadcast daily matches list to Telegram
    try:
        broadcast_schedule()
    except Exception as e:
        print(f"Error broadcasting schedule: {e}")

def job_stream_update():
    print(f"[{datetime.now().isoformat()}] Starting scheduled stream link update...")
    update_live_streams()

@app.on_event("startup")
def startup_event():
    init_db()
    # Run initial scrape and stream update on startup so database is never empty
    print("Running startup scraping tasks...")
    scrape_yallakora()
    update_live_streams()
    
    # Schedule Morning Scrape: Every day at 05:00 AM
    scheduler.add_job(job_morning_scrape, 'cron', hour=5, minute=0)
    # Schedule Stream Link Updater: Every 10 minutes
    scheduler.add_job(job_stream_update, 'interval', minutes=10)
    
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

if __name__ == "__main__":
    import uvicorn
    # Read port from environment (Hugging Face default is 7860)
    port = int(os.getenv("PORT", 7860))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
