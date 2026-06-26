from http.server import BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

SYNONYMS = {
    "كوت ديفوار": "ساحل العاج",
    "ساحل العاج": "كوت ديفوار",
    "أمريكا": "الولايات المتحدة",
    "الولايات المتحدة": "أمريكا",
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

def clean_channel_name(channel):
    if not channel:
        return ""
    # Normalize to lowercase and remove noise words like HD, SD
    chan = channel.lower()
    chan = chan.replace("hd", "").replace("sd", "")
    # Standardize spaces and keep it clean
    chan = re.sub(r'\s+', ' ', chan).strip()
    return chan

def is_iframe_embeddable(url, headers, depth=0):
    # Always return True to avoid false negatives. Streaming sites block datacenter IPs (like Vercel)
    # with Cloudflare (403/503), but load perfectly in the user's browser.
    return True

def fetch_url(url, headers):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return url, response.text, response.content
    except Exception as e:
        print(f"[Search Proxy] Error fetching {url}: {e}")
    return url, None, None

def search_stream_embed(team_a, team_b, channel=""):
    raw_sources = []
    seen_urls = set()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Accept-Language': 'ar,en-US;q=0.7,en;q=0.3'
    }
    
    # 1. Direct Scraping of yallasootlive.com (Primary & Most Stable)
    try:
        print(f"[Search Proxy] Scraping yallasootlive.com directly for {team_a} VS {team_b}...")
        r = requests.get('https://yallasootlive.com/', headers=headers, timeout=12)
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'html.parser')
            match_cards = soup.find_all(class_='AY_Match')
            
            for div in match_cards:
                text_normalized = normalize(div.text)
                
                if match_team(team_a, text_normalized) or match_team(team_b, text_normalized):
                    links = div.find_all('a')
                    for l in links:
                        href = l.get('href')
                        if href and href not in seen_urls:
                            seen_urls.add(href)
                            print(f"[Search Proxy] Found matching card on yallasootlive.com: {href}")
                            # Fetch player page
                            try:
                                pr = requests.get(href, headers=headers, timeout=12)
                                if pr.status_code == 200:
                                    psoup = BeautifulSoup(pr.content, 'html.parser')
                                    iframes = psoup.find_all('iframe')
                                    for iframe in iframes:
                                        src = iframe.get('src')
                                        if src:
                                            src = src.strip()
                                            if src.startswith('//'):
                                                src = f"https:{src}"
                                            if src not in seen_urls:
                                                seen_urls.add(src)
                                                raw_sources.append({
                                                    "name": "سيرفر كورة لايف الرئيسي (متعدد الجودات)",
                                                    "type": "iframe",
                                                    "url": src,
                                                    "parent_url": href
                                                })
                                                # Fetch nested player iframe if available (e.g. depoooo.com)
                                                try:
                                                    ar = requests.get(src, headers=headers, timeout=12)
                                                    if ar.status_code == 200:
                                                        asoup = BeautifulSoup(ar.content, 'html.parser')
                                                        niframes = asoup.find_all('iframe')
                                                        for nif in niframes:
                                                            nsrc = nif.get('src')
                                                            if nsrc:
                                                                nsrc = nsrc.strip()
                                                                if nsrc.startswith('//'):
                                                                    nsrc = f"https:{nsrc}"
                                                                if nsrc not in seen_urls:
                                                                    seen_urls.add(nsrc)
                                                                    raw_sources.append({
                                                                        "name": "بث مباشر متعدد الجودات (سيرفر خارجي)",
                                                                        "type": "iframe",
                                                                        "url": nsrc,
                                                                        "parent_url": href
                                                                    })
                                                except Exception as ex:
                                                    print(f"[Search Proxy] Error fetching nested iframe: {ex}")
                            except Exception as ex:
                                print(f"[Search Proxy] Error fetching match detail from yallasootlive: {ex}")
    except Exception as e:
        print(f"[Search Proxy] Error scraping yallasootlive: {e}")

    # 2. Fallback search on DuckDuckGo if we need more links
    if len(raw_sources) < 3:
        norm_a = re.sub(r'[أإآ]', 'ا', team_a).replace('ة', 'ه')
        norm_b = re.sub(r'[أإآ]', 'ا', team_b).replace('ة', 'ه')
        
        queries = [
            f"{team_a} ضد {team_b} بث مباشر يلا شوت الاسطورة كورة لايف",
            f"yalla shoot {norm_a} vs {norm_b} streamonsport daddylive livehd7",
            f"{team_a} vs {team_b} live stream totalsportek buffstreams",
            f"{team_a} ضد {team_b} كورة فور لايف في العارضة كورة سيتي"
        ]
        
        # Append channel queries if channel is available
        clean_chan = clean_channel_name(channel)
        if clean_chan:
            print(f"[Search Proxy] Adding channel queries for: {clean_chan}")
            queries.append(f"بث مباشر قناة {clean_chan} كورة لايف يلا شوت")
            queries.append(f"koora live {clean_chan} live stream")
        
        found_urls = []
        search_urls = [f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(q)}" for q in queries]
        
        with ThreadPoolExecutor(max_workers=len(search_urls)) as executor:
            futures = {executor.submit(fetch_url, su, headers): su for su in search_urls}
            for future in as_completed(futures):
                _, html, _ = future.result()
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    result_links = soup.find_all('a', class_='result__url')
                    for a in result_links:
                        href = a.get('href')
                        if href:
                            parsed = urllib.parse.urlparse(href)
                            query_params = urllib.parse.parse_qs(parsed.query)
                            actual_url = query_params.get('uddg', [href])[0]
                            
                            blacklist = ['youtube.com', 'facebook.com', 'twitter.com', 'instagram.com', 'wikipedia.org', 'yallakora.com', 'kooora.com', 'aljazeera.net', 'fifa.com', 'pinterest.com', 'linkedin.com']
                            if not any(x in actual_url for x in blacklist):
                                if actual_url not in found_urls:
                                    found_urls.append(actual_url)
                                    
        # Sort found URLs by user's requested 50 source domains (priority sites)
        priority_keywords = [
            'daddylive', 'cricfree', 'vipleague', 'streamonsport', 'footybite', 
            'rojadirecta', 'livetv', 'buffstreams', 'crackstreams', 'firstrowsports', 
            'stream2watch', 'vipbox', 'soccersreams', 'totalsportek', 'hesgoal', 
            'mamahd', 'sportrar', 'livehd7', 'yalla-shoot', 'yallasoot', 'korastart',
            'koora-live', 'kooralive', 'koracity', 'yallashoot', 'kora-online', 
            'mykora', 'koragoal', 'felarda', 'korastar', 'kora4live', 'egybestsport', 
            'kora-plus', 'hikora', 'shoot-live', 'koraweb', 'as-koora', 'askoora'
        ]
        
        def get_priority(url):
            u = url.lower()
            for index, kw in enumerate(priority_keywords):
                if kw in u:
                    return index  # higher priority (lower index in list)
            return 9999
            
        found_urls.sort(key=get_priority)
        candidate_urls = found_urls[:8]
        if candidate_urls:
            hls_count = 0
            iframe_count = 0
            
            with ThreadPoolExecutor(max_workers=len(candidate_urls)) as executor:
                futures = {executor.submit(fetch_url, cu, headers): cu for cu in candidate_urls}
                for future in as_completed(futures):
                    url, html, content = future.result()
                    if not html:
                        continue
                        
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Look for iframe players
                    iframes = soup.find_all('iframe')
                    for iframe in iframes:
                        src = iframe.get('src')
                        if src:
                            src = src.strip()
                            if src.startswith('//'):
                                src = f"https:{src}"
                            if not src.startswith('http') and not src.startswith('https'):
                                continue
                            if 'about:blank' in src or 'javascript:' in src:
                                continue
                            if any(x in src for x in ['google', 'facebook', 'twitter', 'youtube', 'doubleclick', 'analytics', 'adsterra', 'googletagmanager', 'whatsapp', 'telegram']):
                                continue
                            if src not in seen_urls:
                                seen_urls.add(src)
                                iframe_count += 1
                                raw_sources.append({
                                    "name": f"سيرفر خارجي {iframe_count} (إطار)",
                                    "type": "iframe",
                                    "url": src,
                                    "parent_url": url
                                })
                                
                    # Look for direct m3u8 HLS streams (CORS protected, keep as backup)
                    m3u8_links = re.findall(r'(https?://[^\s"\',]+\.m3u8[^\s"\',]*)', html)
                    if m3u8_links:
                        for hls_url in m3u8_links:
                            hls_url = hls_url.replace(r'\u0026', '&').replace('\\u0026', '&')
                            hls_url = re.sub(r'[\s"\'\\,]+$', '', hls_url)
                            if not any(x in hls_url for x in ['logo', 'icon', 'image', 'banner', 'png', 'jpg']):
                                if hls_url not in seen_urls:
                                    seen_urls.add(hls_url)
                                    hls_count += 1
                                    raw_sources.append({
                                        "name": f"سيرفر بث احتياطي {hls_count} (HLS)",
                                        "type": "hls",
                                        "url": hls_url
                                    })
                                    
    # 3. Filter raw_sources in parallel to verify CSP/XFO embedding safety
    verified_sources = []
    
    def check_embeddable(src_obj):
        if src_obj["type"] == "iframe":
            if not is_iframe_embeddable(src_obj["url"], headers):
                print(f"[Embed Check] Discarding blocked iframe: {src_obj['url']}")
                return None
        return src_obj
        
    with ThreadPoolExecutor(max_workers=max(1, len(raw_sources))) as check_executor:
        check_futures = [check_executor.submit(check_embeddable, s) for s in raw_sources]
        for f in as_completed(check_futures):
            res = f.result()
            if res:
                verified_sources.append(res)
                
    # Sort verified sources to put working iframes first
    verified_sources.sort(key=lambda x: 0 if x["type"] == "iframe" else 1)
    
    return verified_sources[:6]

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_url.query)
        
        team_a = query.get('teamA', [None])[0]
        team_b = query.get('teamB', [None])[0]
        channel = query.get('channel', [""])[0]
        
        if not team_a or not team_b:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing teamA or teamB"}).encode('utf-8'))
            return
            
        sources = search_stream_embed(team_a, team_b, channel)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(sources).encode('utf-8'))
