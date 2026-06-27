from http.server import BaseHTTPRequestHandler
import requests
import re
import urllib.parse
import json
import urllib3
urllib3.disable_warnings()

def normalize(text):
    if not text:
        return ""
    text = re.sub(r'[أإآ]', 'ا', text)
    text = re.sub(r'ة', 'ه', text)
    text = re.sub(r'\s+', '', text)
    return text.strip().lower()

def match_team(team, text_normalized):
    norm_team = normalize(team)
    if norm_team in text_normalized:
        return True
        
    if norm_team.startswith("ال"):
        without_al = norm_team[2:]
        if without_al in text_normalized:
            return True
    else:
        with_al = "ال" + norm_team
        if with_al in text_normalized:
            return True
            
    return False

def verify_match_result(title, team_a, team_b):
    title_lower = title.lower()
    norm_title = normalize(title_lower)
    return match_team(team_a, norm_title) and match_team(team_b, norm_title)

def parse_duration_to_seconds(duration_str):
    try:
        parts = list(map(int, duration_str.split(':')))
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
    except Exception:
        pass
    return 0

def find_video_renderers(data):
    renderers = []
    if isinstance(data, dict):
        if 'videoRenderer' in data:
            renderers.append(data['videoRenderer'])
        else:
            for k, v in data.items():
                renderers.extend(find_video_renderers(v))
    elif isinstance(data, list):
        for item in data:
            renderers.extend(find_video_renderers(item))
    return renderers

def search_dailymotion(team_a, team_b):
    query = f"ملخص مباراة {team_a} {team_b}"
    url = f"https://api.dailymotion.com/videos?fields=id,title,duration,embed_url&search={urllib.parse.quote(query)}&limit=15"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    try:
        # We disable verification to prevent SSL handshake errors on Vercel
        r = requests.get(url, headers=headers, timeout=10, verify=False)
        if r.status_code == 200:
            data = r.json()
            videos = data.get('list', [])
            
            valid_videos = []
            for v in videos:
                title = v.get('title', '')
                duration = v.get('duration', 0)
                embed_url = v.get('embed_url', '')
                
                if verify_match_result(title, team_a, team_b):
                    score = 0
                    if duration >= 420: # 7 minutes
                        score += 100
                    elif duration >= 240: # 4 minutes
                        score += 50
                    elif duration >= 120: # 2 minutes
                        score += 10
                        
                    valid_videos.append((embed_url, score))
                    
            if valid_videos:
                valid_videos.sort(key=lambda x: x[1], reverse=True)
                print(f"[Highlights] Found verified Dailymotion highlight: {valid_videos[0][0]}")
                return valid_videos[0][0]
    except Exception as e:
        print(f"[Highlights] Dailymotion search error: {e}")
    return None

def search_youtube(team_a, team_b):
    query = f"ملخص مباراة {team_a} ضد {team_b} كامل".strip()
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Accept-Language': 'ar,en-US;q=0.7,en;q=0.3'
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            best_video_id = None
            
            # Try parsing using the smart ranking algorithm
            try:
                match = re.search(r'var ytInitialData\s*=\s*({.+?});', r.text)
                if match:
                    data = json.loads(match.group(1))
                    renderers = find_video_renderers(data)
                    
                    scored_videos = []
                    blacklist = ['bein sports', 'tod', 'ssc', 'ontime', 'اون تايم', 'أون تايم', 'on time']
                    gameplay_keywords = ['pes', 'fifa 2', 'efootball', 'لعبة', 'العاب', 'محاكاة', 'playstation', 'gameplay']
                    
                    for renderer in renderers:
                        video_id = renderer.get('videoId')
                        if not video_id:
                            continue
                            
                        title = renderer.get('title', {}).get('runs', [{}])[0].get('text', '')
                        duration_str = renderer.get('lengthText', {}).get('simpleText', '')
                        channel = renderer.get('ownerText', {}).get('runs', [{}])[0].get('text', '')
                        
                        duration = parse_duration_to_seconds(duration_str)
                        
                        score = 0
                        
                        # 1. Duration scoring
                        if duration >= 420: # 7 minutes
                            score += 100
                        elif duration >= 240: # 4 minutes
                            score += 50
                        elif duration >= 120: # 2 minutes
                            score += 10
                            
                        # 2. Avoid official channels (they disable embedding - Error 150)
                        channel_lower = channel.lower()
                        for kw in blacklist:
                            if kw in channel_lower:
                                score -= 500
                                break
                                
                        # 3. Avoid gameplay simulations (PES, FIFA, etc.)
                        title_lower = title.lower()
                        for kw in gameplay_keywords:
                            if kw in title_lower:
                                score -= 500
                                break
                                
                        # 4. Title keywords
                        if 'ملخص' in title_lower:
                            score += 20
                        if 'اهداف' in title_lower or 'أهداف' in title_lower:
                            score += 20
                        if 'كامل' in title_lower or 'كاملة' in title_lower:
                            score += 10
                            
                        scored_videos.append((video_id, score))
                        
                    if scored_videos:
                        # Sort by score descending
                        scored_videos.sort(key=lambda x: x[1], reverse=True)
                        best_video_id = scored_videos[0][0]
            except Exception as parse_err:
                print(f"Error in smart highlights parser: {parse_err}")
            
            # Fallback to standard regex if smart parser failed
            if not best_video_id:
                video_ids = []
                json_ids = re.findall(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', r.text)
                if json_ids:
                    video_ids.extend(json_ids)
                link_ids = re.findall(r'\"/watch\?v=([a-zA-Z0-9_-]{11})\"', r.text)
                if link_ids:
                    video_ids.extend(link_ids)
                if video_ids:
                    seen = set()
                    unique_ids = [x for x in video_ids if not (x in seen or seen.add(x))]
                    best_video_id = unique_ids[0]
                    
            if best_video_id:
                return f"https://www.youtube.com/embed/{best_video_id}"
    except Exception as e:
        print(f"[Highlights] YouTube search error: {e}")
    return None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        team_a = query_params.get('teamA', [None])[0]
        team_b = query_params.get('teamB', [None])[0]
        tournament = query_params.get('tournament', [""])[0]
        
        if not team_a or not team_b:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing teamA or teamB"}).encode('utf-8'))
            return
            
        embed_url = None
        
        # 1. First, search Dailymotion (Allows unrestricted embedding!)
        embed_url = search_dailymotion(team_a, team_b)
        
        # 2. If not found on Dailymotion, fallback to YouTube (with smart ranking)
        if not embed_url:
            embed_url = search_youtube(team_a, team_b)
            
        if embed_url:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"embed_url": embed_url}).encode('utf-8'))
            return
            
        self.send_response(404)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"error": "No highlights found"}).encode('utf-8'))
