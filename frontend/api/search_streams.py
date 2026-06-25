from http.server import BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import json

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
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    
    found_urls = []
    
    for query in queries:
        encoded_query = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        try:
            response = requests.get(url, headers=headers, timeout=6)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                result_links = soup.find_all('a', class_='result__url')
                for a in result_links:
                    href = a.get('href')
                    if href:
                        parsed = urllib.parse.urlparse(href)
                        query_params = urllib.parse.parse_qs(parsed.query)
                        actual_url = query_params.get('uddg', [href])[0]
                        
                        # Avoid big general sites to speed up player extraction
                        blacklist = ['youtube.com', 'facebook.com', 'twitter.com', 'instagram.com', 'fifa.com', 'wikipedia.org', 'yallakora.com', 'kooora.com']
                        if not any(x in actual_url for x in blacklist):
                            if actual_url not in found_urls:
                                found_urls.append(actual_url)
        except Exception as e:
            print(f"Search error for {query}: {e}")
            
    # List to store found sources
    sources = []
    seen_urls = set()
    
    # Try extracting HLS or iframe from candidate pages (limited to top 3 for speed)
    for url in found_urls[:3]:
        try:
            response = requests.get(url, headers=headers, timeout=6)
            if response.status_code != 200:
                continue
                
            html = response.text
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 1. Look for direct m3u8 HLS streams
            m3u8_links = re.findall(r'(https?://[^\s"\',]+\.m3u8[^\s"\',]*)', html)
            if m3u8_links:
                for hls_url in m3u8_links:
                    # Clean trailing backslashes, quotes, or formatting chars and replace unicode escaped ampersands
                    hls_url = hls_url.replace(r'\u0026', '&').replace('\\u0026', '&')
                    hls_url = re.sub(r'[\s"\'\\,]+$', '', hls_url)
                    # Filter out logos/images/static assets
                    if not any(x in hls_url for x in ['logo', 'icon', 'image', 'banner', 'png', 'jpg']):
                        if hls_url not in seen_urls:
                            seen_urls.add(hls_url)
                            sources.append({
                                "name": f"سيرفر رئيسي HLS {len(sources)+1}",
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
                        sources.append({
                            "name": f"سيرفر بديل HLS {len(sources)+1}",
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
                    # Skip standard social/ad trackers
                    if any(x in src for x in ['google', 'facebook', 'twitter', 'youtube', 'doubleclick', 'analytics', 'adsterra', 'googletagmanager', 'whatsapp', 'telegram']):
                        continue
                    if src not in seen_urls:
                        seen_urls.add(src)
                        sources.append({
                            "name": f"سيرفر خارجي {len(sources)+1}",
                            "type": "iframe",
                            "url": src
                        })
                        
        except Exception as e:
            print(f"[Search Proxy] Extraction error for {url}: {e}")
            
    return sources[:4]

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
