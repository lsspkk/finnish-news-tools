#!/usr/bin/env python3
import http.server
import socketserver
import json
import os
from pathlib import Path
from urllib.parse import urlparse, parse_qs

PORT = 8080
BASE_DIR = Path(__file__).parent
LOCAL_STORAGE_PATH = BASE_DIR.parent.parent / 'local-dev' / 'storage'

class DevServer(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, HEAD')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()
    
    def do_HEAD(self):
        if self.path.startswith('/api/'):
            self.handle_api_head()
        else:
            super().do_HEAD()
    
    def do_GET(self):
        if self.path.startswith('/api/'):
            self.handle_api_get()
        else:
            super().do_GET()
    
    def do_POST(self):
        if self.path.startswith('/api/'):
            self.handle_api_post()
        else:
            self.send_response(404)
            self.end_headers()
    
    def handle_api_head(self):
        if self.path.startswith('/api/article/'):
            parts = self.path.replace('/api/article/', '').split('/')
            if len(parts) >= 2:
                shortcode = parts[0]
                lang = parts[1]
                article_path = LOCAL_STORAGE_PATH / LOCAL_STORAGE_CONTAINER / 'cache' / 'yle' / 'articles' / f'{shortcode}_{lang}.json'
                if article_path.exists():
                    self.send_response(200)
                    self.end_headers()
                    return
        
        self.send_response(404)
        self.end_headers()
    
    def handle_api_get(self):
        if self.path == '/api/rss-feed':
            self.serve_rss_feed()
        elif self.path.startswith('/api/article/'):
            self.serve_article()
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())
    
    def handle_api_post(self):
        if self.path == '/api/authenticate':
            self.handle_authenticate()
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())
    
    def serve_rss_feed(self):
        rss_path = LOCAL_STORAGE_PATH / 'cache' / 'yle' / 'paauutiset.json'
        
        if not rss_path.exists():
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'RSS feed not found in cache'}).encode())
            return
        
        try:
            with open(rss_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def serve_article(self):
        parts = self.path.replace('/api/article/', '').split('/')
        if len(parts) < 2:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Invalid article path'}).encode())
            return
        
        shortcode = parts[0]
        lang = parts[1]
        article_path = LOCAL_STORAGE_PATH / 'cache' / 'yle' / 'articles' / f'{shortcode}_{lang}.json'
        
        if not article_path.exists():
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Article not found in cache'}).encode())
            return
        
        try:
            with open(article_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_authenticate(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            username = data.get('username', 'user')
            password = data.get('password', '')
            
            if password == 'Hello world!':
                import datetime
                issued_at = datetime.datetime.utcnow().isoformat() + 'Z'
                
                response = {
                    'success': True,
                    'token': 'local-dev-token',
                    'username': username,
                    'issued_at': issued_at,
                    'expires_at': (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat() + 'Z'
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(401)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'error': 'Invalid password'}).encode())
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), DevServer) as httpd:
        print(f"Server running at http://localhost:{PORT}/")
        print(f"Serving files from {BASE_DIR}")
        print(f"Reading cache from {LOCAL_STORAGE_PATH}")
        print("\nPress Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")
