from http.server import BaseHTTPRequestHandler
import requests
from urllib.parse import urlparse, parse_qs, quote

HF_BASE_URL = "https://mmossad824-sports-bot.hf.space"

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse query parameters
        parsed_url = urlparse(self.path)
        query = parse_qs(parsed_url.query)
        target_url = query.get('url', [None])[0]
        
        if not target_url:
            self.send_response(400)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write("<h3>Missing url parameter</h3>".encode('utf-8'))
            return
            
        hf_url = f"{HF_BASE_URL}/api/proxy?url={quote(target_url)}"
        
        try:
            # Fetch proxy response from the Hugging Face Space
            response = requests.get(hf_url, timeout=20)
            self.send_response(response.status_code)
            self.send_header('Content-type', response.headers.get('Content-Type', 'text/html; charset=utf-8'))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.content)
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(f"<h3>Error forwarding request to proxy: {str(e)}</h3>".encode('utf-8'))
