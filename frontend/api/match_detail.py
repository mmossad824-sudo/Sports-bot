from http.server import BaseHTTPRequestHandler
import requests
import json
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse query parameters
        parsed_url = urlparse(self.path)
        query = parse_qs(parsed_url.query)
        match_id = query.get('id', [None])[0]
        
        if not match_id:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing match id"}).encode('utf-8'))
            return
            
        hf_url = f"https://mmossad824-sports-bot.hf.space/api/matches/{match_id}"
        
        try:
            # Fetch match detail from the Hugging Face Space
            response = requests.get(hf_url, timeout=15)
            self.send_response(response.status_code)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.content)
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
