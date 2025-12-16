#!/usr/bin/env python3
"""
Run the complete workflow: scrape, extract, and translate articles using Azure Translator.
"""
import subprocess
import sys
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

# Run translator with Azure provider
# No server needed - Azure Translator is a cloud service
subprocess.run([
    sys.executable,
    "translator/translate_news.py",
    "--translator", "azure"
], check=False)
