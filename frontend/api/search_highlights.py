from http.server import BaseHTTPRequestHandler
import requests
import re
import urllib.parse
import json

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
            
        # Determine the official broadcaster to prioritize high-quality highlights
        broadcaster = ""
        tour_lower = tournament.lower()
        if any(x in tour_lower for x in ["إنجليزي", "انجليزي", "إسباني", "اسباني", "إيطالي", "ايطالي", "فرنسي", "ألماني", "الماني", "أبطال أوروبا", "ابطال اوروبا", "أمم أفريقيا", "امم افريقيا", "أمم أوروبا", "اليورو", "كأس العالم"]):
            broadcaster = "bein sports"
        elif any(x in tour_lower for x in ["سعودي", "روشن", "آسيا", "اسيا"]):
            broadcaster = "ssc"
        elif any(x in tour_lower for x in ["مصر", "الدوري المصري"]):
            broadcaster = "اون تايم"
            
        query = f"ملخص مباراة {team_a} ضد {team_b} كامل {broadcaster}".strip()
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Accept-Language': 'ar,en-US;q=0.7,en;q=0.3'
        }
        
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                video_ids = []
                
                # Pattern 1: JSON videoId field (Highly reliable on modern YouTube search pages)
                json_ids = re.findall(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', r.text)
                if json_ids:
                    video_ids.extend(json_ids)
                    
                # Pattern 2: Standard watch links in quotes
                link_ids = re.findall(r'\"/watch\?v=([a-zA-Z0-9_-]{11})\"', r.text)
                if link_ids:
                    video_ids.extend(link_ids)
                    
                # Pattern 3: Escaped watch links
                escaped_ids = re.findall(r'/watch\?v\\u003d([a-zA-Z0-9_-]{11})', r.text)
                if escaped_ids:
                    video_ids.extend(escaped_ids)
                
                if video_ids:
                    seen = set()
                    unique_ids = [x for x in video_ids if not (x in seen or seen.add(x))]
                    video_id = unique_ids[0]
                    embed_url = f"https://www.youtube.com/embed/{video_id}"
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"video_id": video_id, "embed_url": embed_url}).encode('utf-8'))
                    return
            
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "No highlights found"}).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
