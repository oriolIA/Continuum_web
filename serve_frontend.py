#!/usr/bin/env python3
"""
Simple HTTP server per servir el frontend de Continuum Web
"""

import http.server
import socketserver
import os
from pathlib import Path

PORT = 8080
FRONTEND_DIR = Path(__file__).parent / "frontend"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)
    
    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")

if __name__ == "__main__":
    os.chdir(FRONTEND_DIR)
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"🌬️  Continuum Web Frontend")
        print(f"   URL: http://localhost:{PORT}")
        print(f"   API: http://localhost:8000")
        print(f"\nCtrl+C per aturar")
        httpd.serve_forever()
