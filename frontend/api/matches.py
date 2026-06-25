from http.server import BaseHTTPRequestHandler
import requests
import json

HF_API_URL = "https://mmossad824-sports-bot.hf.space/api/matches"

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Fetch matches from the Hugging Face Space
            response = requests.get(HF_API_URL, timeout=15)
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
