import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import sqlite3
from datetime import datetime
import os
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "matches.db")

SYNONYMS = {
    "كوت ديفوار": "ساحل العاج",
    "ساحل العاج": "كوت ديفوار",
    "أمريكا": "الولايات المتحدة",
    "الولايات المتحدة": "أمريكا",
}

def should_include_match(tour_name, team_a, team_b):
    tour_normalized = tour_name.lower()
    team_a_norm = team_a.lower()
    team_b_norm = team_b.lower()
    
    # Exclude Moroccan League specifically (matches in الدوري المغربي or كأس العرش)
    # But allow Morocco national team matches in World Cup or AFCON
    if "المغربي" in tour_normalized or "كأس العرش" in tour_normalized or "المغرب الفاسي" in team_a_norm or "المغرب الفاسي" in team_b_norm:
        return False
        
    # Whitelist keywords for leagues / tournaments
    whitelist_tournaments = [
        "كأس العالم", "الدوري المصري", "كأس مصر", "السوبر المصري", 
        "كأس العالم للأندية", "دوري أبطال", "الدوري الإنجليزي", 
        "كأس الاتحاد الإنجليزي", "كأس العرب", "كأس الأمم", 
        "الدوري السعودي", "كأس خادم الحرمين الشريفين", "كأس السوبر"
    ]
    
    # Whitelist keywords for key teams
    whitelist_teams = [
        "برشلونة", "ريال مدريد", "أتلتيكو مدريد", "أتليتكو مدريد", 
        "انتر ميامي", "إنتر ميامي", "الهلال", "النصر", "الاتحاد", 
        "الأهلي", "الزمالك", "بيراميدز", "ليفربول", "مانشستر", 
        "أرسنال", "تشيلسي", "بايرن", "باريس", "يوفنتوس"
    ]
    
    # Check tournament whitelist
    for kw in whitelist_tournaments:
        if kw in tour_normalized:
            return True
            
    # Check team whitelist
    for kw in whitelist_teams:
        if kw in team_a_norm or kw in team_b_norm:
            return True
            
    return False

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id TEXT PRIMARY KEY,
            tournament TEXT,
            teamA TEXT,
            teamB TEXT,
            scoreA TEXT,
            scoreB TEXT,
            time TEXT,
            status TEXT,
            channel TEXT,
            round TEXT,
            logoA TEXT,
            logoB TEXT,
            link TEXT,
            stream_type TEXT,
            stream_url TEXT,
            match_date TEXT,
            updated_at TEXT
        )
    """)
    try:
        cursor.execute("ALTER TABLE matches ADD COLUMN match_date TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def save_matches_to_db(matches, match_date):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    
    for m in matches:
        # Create a unique ID using team names and match date
        match_id = f"{m['teamA']}_{m['teamB']}_{match_date}"
        
        # Check if match already exists to preserve stream links
        cursor.execute("SELECT stream_type, stream_url FROM matches WHERE id = ?", (match_id,))
        existing = cursor.fetchone()
        
        stream_type = None
        stream_url = None
        if existing:
            stream_type = existing[0]
            stream_url = existing[1]
            
        cursor.execute("""
            INSERT OR REPLACE INTO matches 
            (id, tournament, teamA, teamB, scoreA, scoreB, time, status, channel, round, logoA, logoB, link, stream_type, stream_url, match_date, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match_id, m['tournament'], m['teamA'], m['teamB'], m['scoreA'], m['scoreB'],
            m['time'], m['status'], m['channel'], m['round'], m['logoA'], m['logoB'],
            m['link'], stream_type, stream_url, match_date, now_str
        ))
        
    conn.commit()
    conn.close()

def format_date_to_db(date_str):
    parts = date_str.split('/')
    if len(parts) == 3:
        month, day, year = parts
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return date_str

def scrape_yallakora(date_str=None):
    from datetime import timedelta
    if not date_str:
        cairo_now = datetime.utcnow() + timedelta(hours=3)
        date_str = f"{cairo_now.month}/{cairo_now.day}/{cairo_now.year}"
        
    db_date = format_date_to_db(date_str)
    url = f"https://www.yallakora.com/match-center/?date={date_str}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    
    print(f"[{datetime.now().isoformat()}] Scraping schedule from Yallakora...")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Error fetching page: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        tournaments = soup.find_all('div', class_='matchCard')
        
        match_list = []
        
        for tour in tournaments:
            tour_title = tour.find('a', class_='tourTitle') or tour.find('div', class_='title')
            tour_name = tour_title.text.strip() if tour_title else "بطولة غير معروفة"
            
            match_ul = tour.find('div', class_='ul')
            if not match_ul:
                continue
                
            match_rows = match_ul.find_all('div', class_='liItem')
            
            for row in match_rows:
                channel_tag = row.find('div', class_='channel')
                channel = channel_tag.text.strip() if channel_tag else ""
                
                round_tag = row.find('div', class_='date')
                match_round = round_tag.text.strip() if round_tag else ""
                
                status_tag = row.find('div', class_='matchStatus')
                status = status_tag.text.strip() if status_tag else "لم تبدأ"
                
                # Team A
                team_a = row.find('div', class_='teamA')
                team_a_name = "فريق أ"
                logo_a = ""
                if team_a:
                    team_a_name = team_a.find('p').text.strip() if team_a.find('p') else team_a.text.strip()
                    img = team_a.find('img')
                    if img:
                        logo_a = img.get('src') or img.get('data-src') or ""
                
                # Team B
                team_b = row.find('div', class_='teamB')
                team_b_name = "فريق ب"
                logo_b = ""
                if team_b:
                    team_b_name = team_b.find('p').text.strip() if team_b.find('p') else team_b.text.strip()
                    img = team_b.find('img')
                    if img:
                        logo_b = img.get('src') or img.get('data-src') or ""
                
                # Filter out uninteresting matches and specifically Moroccan League matches
                if not should_include_match(tour_name, team_a_name, team_b_name):
                    continue
                
                # Result / Time
                score_a = "-"
                score_b = "-"
                match_time = "-"
                
                result_div = row.find('div', class_='MResult')
                if result_div:
                    scores = result_div.find_all('span', class_='score')
                    if len(scores) >= 2:
                        score_a = scores[0].text.strip()
                        score_b = scores[1].text.strip()
                    
                    time_span = result_div.find('span', class_='time')
                    if time_span:
                        match_time = time_span.text.strip()
                
                link_tag = row.find('a')
                match_link = link_tag.get('href') if link_tag else ""
                if match_link and not match_link.startswith('http'):
                    match_link = f"https://www.yallakora.com{match_link}"
                
                classes = row.get('class', [])
                if 'finish' in classes:
                    status_desc = "انتهت"
                elif 'live' in classes or 'now' in classes:
                    status_desc = "جارية الآن"
                elif 'future' in classes:
                    status_desc = "لم تبدأ"
                else:
                    status_desc = status
                
                match_data = {
                    "tournament": tour_name,
                    "teamA": team_a_name,
                    "teamB": team_b_name,
                    "scoreA": score_a,
                    "scoreB": score_b,
                    "time": match_time,
                    "status": status_desc,
                    "channel": channel,
                    "round": match_round,
                    "logoA": logo_a,
                    "logoB": logo_b,
                    "link": match_link
                }
                match_list.append(match_data)
        
        save_matches_to_db(match_list, db_date)
        print(f"Scraped and saved {len(match_list)} matches (filtered).")
        return match_list
    except Exception as e:
        print(f"Error scraping schedule: {e}")
        return []

def search_stream_embed(team_a, team_b, channel=""):
    # Call the Vercel search proxy to bypass Hugging Face Space firewall blocks
    import urllib.parse
    url = f"https://yalla-shoot-today.vercel.app/api/search_streams?teamA={urllib.parse.quote(team_a)}&teamB={urllib.parse.quote(team_b)}&channel={urllib.parse.quote(channel)}"
    try:
        print(f"Calling Vercel stream search proxy for {team_a} VS {team_b} (channel: {channel})...")
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                print(f"Proxy found {len(data)} stream sources.")
                return "multi", json.dumps(data)
            elif isinstance(data, dict):
                stype = data.get("stream_type")
                surl = data.get("stream_url")
                if surl:
                    print(f"Proxy found stream: {surl} ({stype})")
                    return stype, surl
    except Exception as e:
        print(f"Error calling Vercel search proxy: {e}")
        
    return None, None

def update_live_streams():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # We want to find matches that are currently live ("جارية الآن")
    # or starting soon (e.g. status "لم تبدأ") on TODAY's date (Cairo time)
    from datetime import timedelta
    cairo_today = (datetime.utcnow() + timedelta(hours=3)).strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT id, teamA, teamB, stream_url, channel 
        FROM matches 
        WHERE (status = 'جارية الآن' OR status = 'لم تبدأ') 
          AND (match_date = ? OR match_date IS NULL)
    """, (cairo_today,))
    active_matches = cursor.fetchall()
    
    if not active_matches:
        print("No active or upcoming matches to update stream links.")
        conn.close()
        return
        
    print(f"Updating stream links for {len(active_matches)} active/upcoming matches...")
    
    for match_id, team_a, team_b, current_url, channel in active_matches:
        # Always search and update stream links for live/upcoming matches
        stype, surl = search_stream_embed(team_a, team_b, channel)
        if surl:
            print(f"Found live stream(s) for {team_a} VS {team_b}: {surl}")
            cursor.execute("""
                UPDATE matches 
                SET stream_type = ?, stream_url = ?, updated_at = ?
                WHERE id = ?
            """, (stype, surl, datetime.now().isoformat(), match_id))
        else:
            print(f"Could not find stream for {team_a} VS {team_b}")
                
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    scrape_yallakora()
    update_live_streams()
