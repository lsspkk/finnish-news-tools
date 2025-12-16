# Scraper

Scrapes Finnish news articles from YLE.

## Quick Start

- Install: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && playwright install chromium`
- Run from project root with venv activated

## Scripts

- `scraper1.py [search_text]` - Scrapes page, saves HTTP responses to `responses/YYYY-MM-DDTHH-MM-SS/`
- `scraper2.py [search_text]` - Scrapes page, extracts links, downloads articles, creates `articles.html`
- `extract1.py [path]` - Extracts text from saved responses (defaults to latest folder in `responses/`)

## Workflow

1. Scrape: `python scraper/scraper2.py "technology"`
2. Translate: `python translator/translate_news.py` (auto-finds newest `articles.html`)
