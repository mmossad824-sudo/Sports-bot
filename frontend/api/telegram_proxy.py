from http.server import BaseHTTPRequestHandler
import os
import requests
import json

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Read the POST request body
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            payload = json.loads(post_data.decode('utf-8'))
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Invalid JSON payload: {str(e)}"}).encode('utf-8'))
            return
            
        # Extract token dynamically or fallback to env
        token = payload.pop("token", None) or BOT_TOKEN
        if not token:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing bot token"}).encode('utf-8'))
            return
            
        # Forward request to Telegram API
        method = payload.pop("method", "sendMessage")
        url = f"https://api.telegram.org/bot{token}/{method}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=15)
            self.send_response(r.status_code)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(r.content)
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Failed to forward to Telegram: {str(e)}"}).encode('utf-8'))
            
    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
