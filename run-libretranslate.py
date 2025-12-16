#!/usr/bin/env python3
"""
Run the complete workflow: scrape, extract, and translate articles using LibreTranslate.
"""
import subprocess
import sys
import time
import requests
from pathlib import Path
from datetime import datetime

# Check if we need to scrape today
responses_dir = Path("responses")
today_prefix = datetime.now().strftime("%Y-%m-%d")
has_today_data = any(responses_dir.glob(f"{today_prefix}*"))
has_articles = any(responses_dir.rglob("articles.html"))

# Run scraper and extractor if needed
if not has_today_data or not has_articles:
    subprocess.run([sys.executable, "scraper/scraper2.py"], check=False)
    subprocess.run([sys.executable, "scraper/extract2.py"], check=False)

# Start LibreTranslate server
server = subprocess.Popen([
    "libretranslate",
    "--host", "0.0.0.0",
    "--port", "5000"
])

try:
    # Wait for server to be ready (check every second, up to 60 seconds)
    for i in range(60):
        try:
            requests.get("http://localhost:5000", timeout=1)
            break
        except:
            time.sleep(1)
    
    # Run translator
    subprocess.run([sys.executable, "translator/translate_news.py"], check=False)
finally:
    # Stop server
    server.terminate()
