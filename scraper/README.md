# Scraper

## Install

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## Run

### scraper1.py
Scrapes a page and saves all HTTP responses.

```bash
python scraper1.py [search_text]
```

Saves responses to `responses/YYYY-MM-DDTHH-MM-SS/`

### scraper2.py
Scrapes a page, extracts links, and downloads them.

```bash
python scraper2.py [search_text]
```

Saves responses and downloads to timestamped folders.

### extract1.py
Extracts text from saved responses.

```bash
python extract1.py [path]
```

Defaults to latest folder in `responses/`

