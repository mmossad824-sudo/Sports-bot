from http.server import BaseHTTPRequestHandler
import requests
import re
import urllib.parse
import json

SYNONYMS = {
    "كوت ديفوار": "ساحل العاج",
    "ساحل العاج": "كوت ديفوار",
    "أمريكا": "الولايات المتحدة",
    "الولايات المتحدة": "أمريكا",
}

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
        
    # Try stripping "ال" prefix
    if norm_team.startswith("ال"):
        without_al = norm_team[2:]
        if without_al in text_normalized:
            return True
            
    # Try adding "ال" prefix
    else:
        with_al = "ال" + norm_team
        if with_al in text_normalized:
            return True
            
    # Try matching synonyms with/without "ال"
    for k, v in SYNONYMS.items():
        if k in team:
            norm_syn = normalize(v)
            if norm_syn in text_normalized:
                return True
            if norm_syn.startswith("ال"):
                without_al = norm_syn[2:]
                if without_al in text_normalized:
                    return True
            else:
                with_al = "ال" + norm_syn
                if with_al in text_normalized:
                    return True
                    
    return False

def search_dailymotion(team_a, team_b):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        }
        
        # 1. Search in Arabic
        query = f"ملخص مباراة {team_a} و {team_b}"
        url = f"https://api.dailymotion.com/videos?search={urllib.parse.quote(query)}&fields=id,title,embed_url,duration&limit=10&sort=relevance"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            for v in data.get("list", []):
                title = v.get("title", "")
                embed_url = v.get("embed_url")
                duration = v.get("duration", 0)
                
                # Highlights should be >= 90 seconds
                if duration >= 90:
                    title_norm = normalize(title)
                    if match_team(team_a, title_norm) and match_team(team_b, title_norm):
                        return embed_url
                        
        # 2. Search in English translation
        eng_a = TRANSLATIONS.get(team_a.strip())
        eng_b = TRANSLATIONS.get(team_b.strip())
        if eng_a and eng_b:
            query_en = f"{eng_a} vs {eng_b} highlights"
            url_en = f"https://api.dailymotion.com/videos?search={urllib.parse.quote(query_en)}&fields=id,title,embed_url,duration&limit=10&sort=relevance"
            r_en = requests.get(url_en, headers=headers, timeout=10)
            if r_en.status_code == 200:
                data_en = r_en.json()
                for v in data_en.get("list", []):
                    title = v.get("title", "").lower()
                    duration = v.get("duration", 0)
                    embed_url = v.get("embed_url")
                    
                    if duration >= 90:
                        if eng_a.lower() in title and eng_b.lower() in title:
                            return embed_url
    except Exception as e:
        print(f"Error searching Dailymotion: {e}")
    return None

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

        # Try Dailymotion first
        dm_embed = search_dailymotion(team_a, team_b)
        if dm_embed:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"video_id": dm_embed.split('/')[-1], "embed_url": dm_embed}).encode('utf-8'))
            return
            
        # Fallback to YouTube
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
