from http.server import BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import json

def search_stream_embed(team_a, team_b):
    domains = ['yallashot.org', 'yalllalive.com', 'yalla-shoot.sh', 'yella-shoot.live', 'shoots-yalla.com']
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    found_urls = []
    
    # DuckDuckGo HTML Search
    for domain in domains:
        query = f"site:{domain} {team_a} {team_b}"
        encoded_query = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        try:
            response = requests.get(url, headers=headers, timeout=8)
            if response.status_code == 200:
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
            
    # Extract players from candidate pages
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
            
    return None, None

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
            
        stype, surl = search_stream_embed(team_a, team_b)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({
            "stream_type": stype,
            "stream_url": surl
        }).encode('utf-8'))
