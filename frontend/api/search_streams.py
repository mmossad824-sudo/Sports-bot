from http.server import BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_url(url, headers):
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return url, response.text, response.content
    except Exception as e:
        print(f"[Search Proxy] Error fetching {url}: {e}")
    return url, None, None

def search_stream_embed(team_a, team_b):
    # Normalize team names (remove Hamzas) to maximize search matches
    def normalize(text):
        if not text:
            return ""
        text = re.sub(r'[أإآ]', 'ا', text)
        text = re.sub(r'ة', 'ه', text)
        return text.strip()
        
    norm_a = normalize(team_a)
    norm_b = normalize(team_b)
    
    queries = [
        f"{team_a} ضد {team_b} بث مباشر يلا شوت",
        f"yalla shoot {norm_a} vs {norm_b}"
    ]
    
    # Use simple User-Agent that DuckDuckGo does not rate limit/block
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    
    found_urls = []
    
    # Fetch DDG search queries in parallel
    search_urls = [f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(q)}" for q in queries]
    
    with ThreadPoolExecutor(max_workers=2) as executor:
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
                        
                        # Avoid big general sites to speed up player extraction
                        blacklist = ['youtube.com', 'facebook.com', 'twitter.com', 'instagram.com', 'wikipedia.org', 'yallakora.com', 'kooora.com', 'aljazeera.net', 'fifa.com']
                        if not any(x in actual_url for x in blacklist):
                            if actual_url not in found_urls:
                                found_urls.append(actual_url)
                                
    # List to store found sources
    sources = []
    seen_urls = set()
    
    # We will fetch up to 6 candidate pages in parallel for extraction
    candidate_urls = found_urls[:6]
    if not candidate_urls:
        return []
        
    hls_count = 0
    iframe_count = 0
    
    with ThreadPoolExecutor(max_workers=len(candidate_urls)) as executor:
        futures = {executor.submit(fetch_url, cu, headers): cu for cu in candidate_urls}
        for future in as_completed(futures):
            url, html, content = future.result()
            if not html:
                continue
                
            soup = BeautifulSoup(content, 'html.parser')
            
            # 1. Look for direct m3u8 HLS streams
            m3u8_links = re.findall(r'(https?://[^\s"\',]+\.m3u8[^\s"\',]*)', html)
            if m3u8_links:
                for hls_url in m3u8_links:
                    hls_url = hls_url.replace(r'\u0026', '&').replace('\\u0026', '&')
                    hls_url = re.sub(r'[\s"\'\\,]+$', '', hls_url)
                    # Filter out logos/images/static assets
                    if not any(x in hls_url for x in ['logo', 'icon', 'image', 'banner', 'png', 'jpg']):
                        if hls_url not in seen_urls:
                            seen_urls.add(hls_url)
                            hls_count += 1
                            sources.append({
                                "name": f"بث رئيسي HD {hls_count} (HLS)",
                                "type": "hls",
                                "url": hls_url
                            })
                            
            # 2. Check for JS HLS player configs
            js_sources = re.findall(r'source\s*:\s*["\'](https?://.*?\.m3u8.*?)["\']', html)
            if js_sources:
                for js_url in js_sources:
                    js_url = js_url.replace(r'\u0026', '&').replace('\\u0026', '&')
                    js_url = re.sub(r'[\s"\'\\,]+$', '', js_url)
                    if js_url not in seen_urls:
                        seen_urls.add(js_url)
                        hls_count += 1
                        sources.append({
                            "name": f"بث احتياطي SD {hls_count} (HLS)",
                            "type": "hls",
                            "url": js_url
                        })
                        
            # 3. Check for iframe players
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
                        sources.append({
                            "name": f"سيرفر خارجي متعدد الجودات {iframe_count}",
                            "type": "iframe",
                            "url": src
                        })
                        
    return sources[:6]

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_url.query)
        
        team_a = query.get('teamA', [None])[0]
        team_b = query.get('teamB', [None])[0]
        
        if not team_a or not team_b:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing teamA or teamB"}).encode('utf-8'))
            return
            
        sources = search_stream_embed(team_a, team_b)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(sources).encode('utf-8'))
