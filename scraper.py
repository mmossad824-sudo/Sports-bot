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
        "الدوري السعودي", "كأس خادم الحرمين الشريفين", "كأس السوبر",
        "الدوري الإسباني", "الدوري الإيطالي", "الدوري الألماني", 
        "الدوري الفرنسي", "الدوري الأوروبي", "دوري المؤتمر الأوروبي", 
        "كأس ملك إسبانيا", "كأس إيطاليا", "كأس الرابطة الإنجليزية", "كأس إسبانيا"
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
            updated_at TEXT,
            telegram_start_sent INTEGER DEFAULT 0,
            telegram_half_sent INTEGER DEFAULT 0,
            telegram_end_sent INTEGER DEFAULT 0,
            last_telegram_scoreA TEXT,
            last_telegram_scoreB TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS match_highlights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT,
            platform TEXT,
            video_url TEXT
        )
    """)
    
    # Run migrations for all potentially missing columns
    columns = [
        ("match_date", "TEXT"),
        ("telegram_start_sent", "INTEGER DEFAULT 0"),
        ("telegram_half_sent", "INTEGER DEFAULT 0"),
        ("telegram_end_sent", "INTEGER DEFAULT 0"),
        ("last_telegram_scoreA", "TEXT"),
        ("last_telegram_scoreB", "TEXT"),
        ("telegram_embed_url", "TEXT"),
        ("mid_match_clip_uploaded", "INTEGER DEFAULT 0")
    ]
    for col_name, col_type in columns:
        try:
            cursor.execute(f"ALTER TABLE matches ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass # Column already exists
            
    conn.commit()
    conn.close()

def save_matches_to_db(matches, match_date):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    
    for m in matches:
        # Create a unique ID using team names and match date
        match_id = f"{m['teamA']}_{m['teamB']}_{match_date}"
        
        # Check if match already exists to preserve stream links and alert statuses
        cursor.execute("""
            SELECT id, stream_type, stream_url, last_telegram_scoreA, last_telegram_scoreB 
            FROM matches 
            WHERE id = ?
        """, (match_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Match exists, update details but preserve stream_url if not empty
            stream_type_db = existing[1]
            stream_url_db = existing[2]
            last_score_a = existing[3]
            last_score_b = existing[4]
            
            # If last_telegram_scoreA is not initialized, initialize it with current score
            if last_score_a is None:
                cursor.execute("""
                    UPDATE matches 
                    SET tournament = ?, scoreA = ?, scoreB = ?, time = ?, status = ?, channel = ?, round = ?, logoA = ?, logoB = ?, link = ?, match_date = ?, updated_at = ?, last_telegram_scoreA = ?, last_telegram_scoreB = ?
                    WHERE id = ?
                """, (
                    m['tournament'], m['scoreA'], m['scoreB'], m['time'], m['status'], m['channel'], m['round'], m['logoA'], m['logoB'], m['link'], match_date, now_str, m['scoreA'], m['scoreB'], match_id
                ))
            else:
                cursor.execute("""
                    UPDATE matches 
                    SET tournament = ?, scoreA = ?, scoreB = ?, time = ?, status = ?, channel = ?, round = ?, logoA = ?, logoB = ?, link = ?, match_date = ?, updated_at = ?
                    WHERE id = ?
                """, (
                    m['tournament'], m['scoreA'], m['scoreB'], m['time'], m['status'], m['channel'], m['round'], m['logoA'], m['logoB'], m['link'], match_date, now_str, match_id
                ))
        else:
            # Match doesn't exist, insert new row and initialize last scores to prevent false goal alerts
            cursor.execute("""
                INSERT INTO matches 
                (id, tournament, teamA, teamB, scoreA, scoreB, time, status, channel, round, logoA, logoB, link, stream_type, stream_url, match_date, updated_at, telegram_start_sent, telegram_half_sent, telegram_end_sent, last_telegram_scoreA, last_telegram_scoreB, mid_match_clip_uploaded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?, 0)
            """, (
                match_id, m['tournament'], m['teamA'], m['teamB'], m['scoreA'], m['scoreB'],
                m['time'], m['status'], m['channel'], m['round'], m['logoA'], m['logoB'],
                m['link'], None, None, match_date, now_str, m['scoreA'], m['scoreB']
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
                        if logo_a:
                            logo_a = logo_a.replace('\\', '/')
                
                # Team B
                team_b = row.find('div', class_='teamB')
                team_b_name = "فريق ب"
                logo_b = ""
                if team_b:
                    team_b_name = team_b.find('p').text.strip() if team_b.find('p') else team_b.text.strip()
                    img = team_b.find('img')
                    if img:
                        logo_b = img.get('src') or img.get('data-src') or ""
                        if logo_b:
                            logo_b = logo_b.replace('\\', '/')
                
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
    cairo_now = datetime.utcnow() + timedelta(hours=3)
    cairo_today = cairo_now.strftime("%Y-%m-%d")
    
    cursor.execute("""
        SELECT id, teamA, teamB, stream_type, stream_url, channel, status, time 
        FROM matches 
        WHERE (status = 'جارية الآن' OR status = 'لم تبدأ' OR status LIKE '%الشوط%' OR status LIKE '%بين%') 
          AND (match_date = ? OR match_date IS NULL)
    """, (cairo_today,))
    active_matches = cursor.fetchall()
    
    if not active_matches:
        print("No active or upcoming matches to update stream links.")
        conn.close()
        return
        
    print(f"Checking stream links for {len(active_matches)} active/upcoming matches...")
    
    updated_count = 0
    for match_id, team_a, team_b, current_type, current_url, channel, status, time_str in active_matches:
        # Determine if we should search for streams now (if live or starting in < 30 minutes)
        should_update = False
        if status == 'جارية الآن' or 'الشوط' in status or 'بين' in status:
            should_update = True
        elif status == 'لم تبدأ' and time_str and ':' in time_str:
            try:
                match_hour, match_min = map(int, time_str.split(':'))
                match_dt = cairo_now.replace(hour=match_hour, minute=match_min, second=0, microsecond=0)
                diff = (match_dt - cairo_now).total_seconds()
                # If match starts in <= 30 minutes (1800 seconds) and we haven't reached more than 2 hours past scheduled start
                if -7200 <= diff <= 1800:
                    should_update = True
            except Exception as ex:
                print(f"Error parsing time for match {team_a} VS {team_b}: {ex}")
                should_update = True # fallback to safe update if parse fails
        else:
            # Safe default
            should_update = True
            
        if not should_update:
            print(f"Skipping stream search for {team_a} VS {team_b} (starts at {time_str}) - too early.")
            continue
            
        print(f"Updating stream links for {team_a} VS {team_b}...")
        stype, surl = search_stream_embed(team_a, team_b, channel)
        
        # Parse existing sources
        existing_sources = []
        if current_url:
            if current_url.startswith('['):
                try:
                    existing_sources = json.loads(current_url)
                except Exception:
                    pass
            else:
                existing_sources = [{"name": "البث الرئيسي", "type": current_type or "hls", "url": current_url}]
                
        if surl:
            new_sources = []
            if stype == 'multi':
                try:
                    new_sources = json.loads(surl)
                except Exception:
                    pass
            else:
                new_sources = [{"name": "سيرفر بث", "type": stype, "url": surl}]
                
            # Merge sources (avoiding duplicates)
            merged = list(existing_sources)
            existing_urls = {s["url"] for s in existing_sources}
            
            for ns in new_sources:
                if ns["url"] not in existing_urls:
                    ns["name"] = f"سيرفر إضافي {len(merged) + 1}"
                    merged.append(ns)
                    
            if merged:
                final_url = json.dumps(merged)
                final_type = "multi"
                
                print(f"Found live stream(s) for {team_a} VS {team_b}. Total sources merged: {len(merged)}")
                cursor.execute("""
                    UPDATE matches 
                    SET stream_type = ?, stream_url = ?, updated_at = ?
                    WHERE id = ?
                """, (final_type, final_url, datetime.now().isoformat(), match_id))
                updated_count += 1
        else:
            print(f"Could not find new streams for {team_a} VS {team_b}. Preserving existing streams.")
                
    conn.commit()
    conn.close()
    print(f"Stream links update finished. Updated {updated_count} matches.")

def get_scorebat_embed_url(team_a, team_b):
    TRANSLATIONS = {
        "برشلونة": "barcelona",
        "ريال مدريد": "real madrid",
        "أتلتيكو مدريد": "atletico madrid",
        "أتليتكو مدريد": "atletico madrid",
        "ليفربول": "liverpool",
        "مانشستر سيتي": "manchester city",
        "مانشستر يونايتد": "manchester united",
        "أرسنال": "arsenal",
        "ارسنال": "arsenal",
        "تشيلسي": "chelsea",
        "توتنهام": "tottenham",
        "بايرن ميونخ": "bayern",
        "بايرن": "bayern",
        "باريس سان جيرمان": "psg",
        "باريس": "psg",
        "يوفنتوس": "juventus",
        "إنتر ميلان": "inter",
        "انتر ميلان": "inter",
        "ميلان": "ac milan",
        "روما": "roma",
        "نابولي": "napoli",
        "بروسيا دورتموند": "dortmund",
        "دورتموند": "dortmund",
        "أياكس": "ajax",
        "اياكس": "ajax",
        "النرويج": "norway",
        "فرنسا": "france",
        "اليابان": "japan",
        "السويد": "sweden",
        "تونس": "tunisia",
        "هولندا": "netherlands",
        "باراجواي": "paraguay",
        "باراغواي": "paraguay",
        "أستراليا": "australia",
        "تركيا": "turkey",
        "أمريكا": "usa",
        "السنغال": "senegal",
        "العراق": "iraq",
        "بلجيكا": "belgium",
        "إسبانيا": "spain",
        "اسبانيا": "spain",
        "إنجلترا": "england",
        "انجلترا": "england",
        "البرتغال": "portugal",
        "كرواتيا": "croatia",
        "الأرجنتين": "argentina",
        "الارجنتين": "argentina",
        "البرازيل": "brazil",
        "المغرب": "morocco",
        "هايتى": "haiti",
        "هايتي": "haiti",
        "إسكتلندا": "scotland",
        "اسكتلندا": "scotland",
        "التشيك": "czech",
        "المكسيك": "mexico",
        "جنوب أفريقيا": "south africa",
        "جنوب افريقيا": "south africa",
        "كوريا الجنوبية": "south korea",
        "إكوادور": "ecuador",
        "اكوادور": "ecuador",
        "أوروغواي": "uruguay",
        "أوروجواي": "uruguay",
        "إيطاليا": "italy",
    }
    
    eng_a = TRANSLATIONS.get(team_a.strip())
    eng_b = TRANSLATIONS.get(team_b.strip())
    
    if not eng_a or not eng_b:
        return None
        
    try:
        url = "https://www.scorebat.com/video-api/v3/"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            for item in data.get("response", []):
                title = item.get("title", "").lower()
                home = item.get("homeTeam", {}).get("name", "").lower()
                away = item.get("awayTeam", {}).get("name", "").lower()
                
                # Check if both teams match
                match_home = (eng_a in home or eng_a in title)
                match_away = (eng_b in away or eng_b in title)
                
                # Check reverse match just in case
                match_home_rev = (eng_b in home or eng_b in title)
                match_away_rev = (eng_a in away or eng_a in title)
                
                if (match_home and match_away) or (match_home_rev and match_away_rev):
                    videos = item.get("videos", [])
                    if videos:
                        embed_code = videos[0].get("embed", "")
                        match_url = re.search(r"src='([^']+)'", embed_code) or re.search(r'src="([^"]+)"', embed_code)
                        if match_url:
                            return match_url.group(1)
    except Exception as e:
        print(f"[ScoreBat] Error searching highlights: {e}")
        
    return None

def update_finished_matches_highlights():
    # Find recently finished matches (status is "انتهت") that do not have a youtube/highlight link in stream_url
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    from datetime import timedelta
    cairo_now = datetime.utcnow() + timedelta(hours=3)
    cairo_today = cairo_now.strftime("%Y-%m-%d")
    
    cursor.execute("""
        SELECT id, teamA, teamB, tournament, stream_url 
        FROM matches 
        WHERE status = 'انتهت' 
          AND (stream_url IS NULL OR (stream_url NOT LIKE '%scorebat%' AND stream_url NOT LIKE '%youtube%' AND stream_url NOT LIKE '%youtu.be%'))
    """)
    
    finished_matches = cursor.fetchall()
    if not finished_matches:
        conn.close()
        return
        
    print(f"[Highlights] Found {len(finished_matches)} finished matches needing highlights.")
    
    # We call our Vercel highlights search proxy to bypass the Hugging Face Space outbound blocks
    website_url = os.getenv("WEBSITE_URL", "https://yalla-shoot-today.vercel.app")
    
    for match_id, team_a, team_b, tournament, stream_url in finished_matches:
        # ScoreBat bypassed - User requested YouTube highlights only
        # embed_url = get_scorebat_embed_url(team_a, team_b)
        embed_url = None
            
        # If not found on ScoreBat, fallback to Vercel YouTube highlights search proxy
        import urllib.parse
        
        # Route through Vercel highlights search API
        url = f"{website_url.rstrip('/')}/api/search_highlights?teamA={urllib.parse.quote(team_a)}&teamB={urllib.parse.quote(team_b)}&tournament={urllib.parse.quote(tournament)}"
        
        try:
            print(f"[Highlights] Calling Vercel proxy to fetch highlights for {team_a} VS {team_b}...")
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                data = r.json()
                embed_url = data.get("embed_url")
                if embed_url:
                    print(f"[Highlights] Proxy successfully found embed: {embed_url}")
                    sources = [{
                        "name": "ملخص وأهداف المباراة",
                        "type": "iframe",
                        "url": embed_url
                    }]
                    sources_json = json.dumps(sources)
                    
                    cursor.execute("""
                        UPDATE matches 
                        SET stream_type = 'multi', stream_url = ?, updated_at = ? 
                        WHERE id = ?
                    """, (sources_json, datetime.now().isoformat(), match_id))
                    print(f"[Highlights] Successfully updated highlights for {team_a} VS {team_b}")
                    
                    # Spawn a background process to download and upload the video to Telegram
                    import subprocess
                    import sys
                    script_path = os.path.join(os.path.dirname(__file__), "upload_video_to_telegram.py")
                    # We pass the Dailymotion URL or YouTube URL (Dailymotion is better for yt-dlp downloading as it's not blocked as often)
                    source_url = None
                    if "dailymotion" in embed_url:
                        source_url = f"https://www.dailymotion.com/video/{data.get('video_id')}"
                    elif "youtube" in embed_url:
                        source_url = f"https://www.youtube.com/watch?v={data.get('video_id')}"
                        
                    if source_url:
                        print(f"[Highlights] Spawning background Telegram upload task for {team_a} VS {team_b}...")
                        subprocess.Popen([sys.executable, script_path, match_id, team_a, team_b, source_url])
                    
                else:
                    print(f"[Highlights] Proxy returned empty embed URL for {team_a} VS {team_b}")
            else:
                print(f"[Highlights] Proxy returned error status {r.status_code} for {team_a} VS {team_b}")
        except Exception as e:
            print(f"[Highlights] Proxy error fetching highlights for {team_a} VS {team_b}: {e}")
            
    conn.commit()
    conn.close()

def catch_live_goals():
    """Find live matches and fetch mid-match clips (goals) to upload immediately."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    from datetime import timedelta
    cairo_now = datetime.utcnow() + timedelta(hours=3)
    cairo_today = cairo_now.strftime("%Y-%m-%d")
    
    # Matches that are currently live and haven't had a clip uploaded yet
    cursor.execute("""
        SELECT id, teamA, teamB 
        FROM matches 
        WHERE (status = 'جارية الآن' OR status LIKE '%الشوط%')
          AND mid_match_clip_uploaded = 0
          AND (match_date = ? OR match_date IS NULL)
    """, (cairo_today,))
    
    live_matches = cursor.fetchall()
    if not live_matches:
        conn.close()
        return
        
    print(f"[Mid-Match Clips] Checking {len(live_matches)} live matches for goals...")
    
    for match_id, team_a, team_b in live_matches:
        embed_url = get_scorebat_embed_url(team_a, team_b)
        if embed_url:
            print(f"[Mid-Match Clips] Found clip for {team_a} VS {team_b} -> {embed_url}")
            
            # Spawn background uploader
            import subprocess
            import sys
            script_path = os.path.join(os.path.dirname(__file__), "upload_match_highlights.py")
            subprocess.Popen([sys.executable, script_path, match_id, team_a, team_b, embed_url])
            
            # Mark as uploaded so we don't spam
            cursor.execute("UPDATE matches SET mid_match_clip_uploaded = 1 WHERE id = ?", (match_id,))
            
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    scrape_yallakora()
    update_live_streams()
    catch_live_goals()
    update_finished_matches_highlights()
