import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import sqlite3
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "matches.db")

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
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_matches_to_db(matches):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    
    for m in matches:
        # Create a unique ID using team names and today's date
        today_date = datetime.now().strftime("%Y-%m-%d")
        match_id = f"{m['teamA']}_{m['teamB']}_{today_date}"
        
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
            (id, tournament, teamA, teamB, scoreA, scoreB, time, status, channel, round, logoA, logoB, link, stream_type, stream_url, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match_id, m['tournament'], m['teamA'], m['teamB'], m['scoreA'], m['scoreB'],
            m['time'], m['status'], m['channel'], m['round'], m['logoA'], m['logoB'],
            m['link'], stream_type, stream_url, now_str
        ))
        
    conn.commit()
    conn.close()

def scrape_yallakora(date_str=None):
    if not date_str:
        now = datetime.now()
        date_str = f"{now.month}/{now.day}/{now.year}"
    
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
                elif 'live' in classes:
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
        
        save_matches_to_db(match_list)
        print(f"Scraped and saved {len(match_list)} matches.")
        return match_list
    except Exception as e:
        print(f"Error scraping schedule: {e}")
        return []

def search_stream_embed(team_a, team_b):
    domains = ['yallashot.org', 'yalllalive.com', 'yalla-shoot.sh', 'yella-shoot.live', 'shoots-yalla.com']
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    
    found_urls = []
    
    # Try search engines for candidate pages
    for domain in domains:
        query = f"site:{domain} {team_a} {team_b}"
        encoded_query = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        try:
            response = requests.get(url, headers=headers, timeout=8)
            if response.status_code != 200:
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')
            result_links = soup.find_all('a', class_='result__url')
            
            for a in result_links:
                href = a.get('href')
                if href:
                    parsed = urllib.parse.urlparse(href)
                    query_params = urllib.parse.parse_qs(parsed.query)
                    actual_url = query_params.get('uddg', [href])[0]
                    if domain in actual_url:
                        found_urls.append(actual_url)
        except Exception as e:
            print(f"Search error for {domain}: {e}")
            
    # Try extracting embed players from pages
    for url in found_urls[:4]:
        try:
            response = requests.get(url, headers=headers, timeout=8)
            if response.status_code != 200:
                continue
                
            html = response.text
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check for direct m3u8
            m3u8_links = re.findall(r'(https?://[^\s"\',]+\.m3u8[^\s"\',]*)', html)
            if m3u8_links:
                # filter out obvious bad URLs or static resources
                hls_url = m3u8_links[0]
                if not any(x in hls_url for x in ['logo', 'icon', 'image']):
                    return "hls", hls_url
                    
            # Check for iframe players
            iframes = soup.find_all('iframe')
            for iframe in iframes:
                src = iframe.get('src')
                if src:
                    if src.startswith('//'):
                        src = f"https:{src}"
                    if any(x in src for x in ['google', 'facebook', 'twitter', 'youtube', 'doubleclick', 'analytics', 'adsterra', 'googletagmanager']):
                        continue
                    return "iframe", src
                    
            # Check JS HLS player config
            js_sources = re.findall(r'source\s*:\s*["\'](https?://.*?\.m3u8.*?)["\']', html)
            if js_sources:
                return "hls", js_sources[0]
                
        except Exception as e:
            print(f"Extraction error for {url}: {e}")
            
    # Fallback structure: Search general Web Player
    # You can return a fallback player aggregator URL if nothing is found
    # E.g. search generally on duckduckgo for a streaming frame
    return None, None

def update_live_streams():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # We want to find matches that are currently live ("جارية الآن")
    # or starting soon (e.g. status "لم تبدأ")
    cursor.execute("SELECT id, teamA, teamB, stream_url FROM matches WHERE status = 'جارية الآن' OR status = 'لم تبدأ'")
    active_matches = cursor.fetchall()
    
    if not active_matches:
        print("No active or upcoming matches to update stream links.")
        conn.close()
        return
        
    print(f"Updating stream links for {len(active_matches)} active/upcoming matches...")
    
    for match_id, team_a, team_b, current_url in active_matches:
        # If we already have a stream link, check if we need to refresh it (or keep it)
        # For simplicity, we search for a link if none exists
        if not current_url:
            stype, surl = search_stream_embed(team_a, team_b)
            if surl:
                print(f"Found live stream for {team_a} VS {team_b}: {surl}")
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
