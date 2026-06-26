from http.server import BaseHTTPRequestHandler
import requests
import re
import urllib.parse
import json

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
            
        # Do not append broadcaster name to prevent official channels that block embedding (Error 150)
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
                    embed_url = f"https://www.youtube.com/embed/{best_video_id}"
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"video_id": best_video_id, "embed_url": embed_url}).encode('utf-8'))
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
