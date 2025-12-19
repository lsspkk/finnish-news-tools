# Azure Functions Plan: RSS Feed Parser & Article Scraper

## Overview

Two Azure Functions for fetching and processing Finnish news articles:
1. RSS Feed Parser Function: Fetches RSS feed, parses to JSON, saves to Azure Blob Storage
2. Article Scraper Function: Scrapes article content from RSS links, extracts text/paragraphs, saves to Azure Blob Storage

---

## Function 1: RSS Feed Parser (rss_feed_parser)

### Purpose
- Fetch RSS feed from https://yle.fi/rss/uutiset/paauutiset
- Parse RSS XML to structured JSON
- Save JSON to Azure Blob Storage with TTL
- Cleanup expired cache entries before fetching

### Trigger
- HTTP Trigger (GET/POST) - frontend/manual invocation


### Input
- RSS feed URL (from config or environment variable)
- Optional: ?origin=rss suffix toggle (from config)
- Optional: ?force_reload=true to bypass cache and fetch fresh data

### Output
- JSON file saved to Azure Blob Storage:

    finnish-news-tools/cache/yle/paauutiset.json

### Cache TTL
- Configurable TTL via CACHE_TTL_HOURS setting
- Default: 1 hour for RSS feeds (frequent updates)
- Can be set to 24 hours if needed
- Cache includes expires_at timestamp
- Expired cache entries are automatically cleaned up before each fetch

### JSON Structure

    {
      "feed_metadata": {
        "title": "Yle Uutiset | Pääuutiset",
        "description": "Ylen pääuutiset nopeasti ja luotettavasti",
        "link": "https://yle.fi/uutiset",
        "language": "fi",
        "last_build_date": "Thu, 18 Dec 2025 09:51:22 +0200",
        "fetch_timestamp": "2025-12-18T09:51:22Z"
      },
      "items": [
        {
          "title": "Article title",
          "link": "https://yle.fi/a/74-20197424?origin=rss",
          "description": "Article description",
          "guid": "https://yle.fi/a/74-20197424",
          "pub_date": "Thu, 18 Dec 2025 07:13:23 +0200",
          "categories": ["Sosiaalinen media", "Facebook"],
          "shortcode": "74-20197424"
        }
      ],
      "expires_at": "2025-12-18T10:51:22Z",
      "cache_ttl_hours": 1
    }

### Dependencies
- feedparser - RSS/Atom parsing
- azure-storage-blob - Azure Blob Storage SDK
- azure-functions - Azure Functions runtime

### Rate Limiting
- Daily request limit: 50 requests per day (configurable)
- Tracked in Azure Table Storage
- Returns 429 Too Many Requests when limit exceeded
- Request count resets at midnight UTC

### Code Structure
    azure-one/scraper-one/functions/
    ├── rss_feed_parser/
    │   ├── __init__.py          # Main function entry point
    │   ├── rss_parser.py        # RSS parsing logic
    │   └── storage_client.py    # Azure Blob Storage wrapper
    ├── shared/
    │   ├── token_validator.py   # Token validation
    │   ├── rate_limiter.py      # Daily request rate limiter
    │   ├── storage_client.py    # Shared storage utilities
    │   └── cache_cleaner.py    # Shared cache cleanup logic

---

## Function 2: Article Scraper (article_scraper)

### Purpose
- Fetch article HTML from RSS feed links
- Extract title and text paragraphs (as if browser loaded it)
- Save extracted content to Azure Blob Storage with TTL
- Cleanup expired cache entries before scraping

### Trigger
- HTTP Trigger (GET/POST) - frontend/manual invocation

### Input
- Article URL(s) from RSS feed JSON
- Configurable: add/remove ?origin=rss suffix
- Language code (default: "fi") - used in filename: {shortcode}_{language_code}.json
- Parsing rules from YAML config file

### Output
- JSON file per article saved to Azure Blob Storage:

    finnish-news-tools/cache/yle/articles/{shortcode}_{language_code}.json

### Cache TTL
- Configurable TTL via CACHE_TTL_HOURS setting
- Default: 1 hour for articles (frequent updates)
- Can be set to 24 hours if needed
- Cache includes expires_at timestamp
- Expired cache entries are automatically cleaned up before each scrape

### JSON Structure

    {
      "url": "https://yle.fi/a/74-20197424",
      "shortcode": "74-20197424",
      "title": "Article Title",
      "paragraphs": [
        "First paragraph text...",
        "Second paragraph text...",
        "Third paragraph text..."
      ],
      "scraped_at": "2025-12-18T09:51:22Z",
      "scraper_version": "1.0",
      "expires_at": "2025-12-18T10:51:22Z",
      "cache_ttl_hours": 1
    }

### Scraping Library
- BeautifulSoup4 (recommended for Azure Functions)
  - Lightweight, no browser needed
  - Works well in serverless environment
  - Fast parsing
  - Good for static HTML content

### Alternative: Requests-HTML (if JavaScript rendering needed)
- Only use if BeautifulSoup fails to extract content
- Heavier, requires more resources

### Parsing Rules (YAML Config)

    # scraper-config.yaml
    scraping:
      # Base URL patterns
      base_urls:
        - "https://yle.fi/a/"
      
      # Selectors for article content
      selectors:
        title:
          - "h1.article-title"
          - "h1"
          - ".article-header h1"
          - "title"
        
        paragraphs:
          - "article p"
          - ".article-content p"
          - ".article-body p"
          - "main p"
          - ".content p"
        
        # Elements to exclude
        exclude:
          - ".advertisement"
          - ".social-share"
          - ".related-articles"
          - "footer"
          - "nav"
          - "script"
          - "style"
      
      # Text cleaning rules
      cleaning:
        remove_empty: true
        min_length: 20  # Minimum paragraph length
        strip_whitespace: true
        remove_newlines: false  # Keep newlines for readability
      
      # URL handling
      url:
        add_origin_rss: true  # Add ?origin=rss suffix
        remove_existing_params: false  # Keep existing query params
      
      # Request settings
      request:
        timeout: 30
        headers:
          User-Agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
          Accept-Language: "fi-FI,fi;q=0.9,en;q=0.8"
        follow_redirects: true
        max_redirects: 5

### Dependencies
- beautifulsoup4 - HTML parsing
- lxml or html.parser - BeautifulSoup parser backend
- requests - HTTP client
- pyyaml - YAML config parsing
- azure-storage-blob - Azure Blob Storage SDK
- azure-functions - Azure Functions runtime

### Rate Limiting
- Daily request limit: 50 requests per day (configurable)
- Tracked in Azure Table Storage
- Returns 429 Too Many Requests when limit exceeded
- Request count resets at midnight UTC

### Code Structure

    azure-one/scraper-one/functions/
    ├── article_scraper/
    │   ├── __init__.py              # Main function entry point
    │   ├── scraper.py               # BeautifulSoup scraping logic
    │   ├── config_loader.py         # YAML config loader
    │   └── storage_client.py        # Azure Blob Storage wrapper
    ├── shared/
    │   ├── rate_limiter.py          # Daily request rate limiter
    │   ├── storage_client.py        # Shared storage utilities
    │   ├── cache_cleaner.py         # Shared cache cleanup logic
    │   └── utils.py                 # Shared utilities
    └── scraper-config.yaml          # Parsing rules configuration

---

## Azure Blob Storage Structure

Storage structure:

    finnish-news-tools/
    └── cache/
        └── yle/
            ├── paauutiset.json
            └── articles/
                ├── 74-20197424_fi.json
                ├── 74-20197424_en.json
                ├── 74-20199829_fi.json
                └── 74-20200396_fi.json

---

## Configuration Files

### 1. scraper-config.yaml (Article Scraper Rules)
Location: azure-one/scraper-one/functions/scraper-config.yaml

See YAML structure above in "Parsing Rules" section.

### 2. function-app-settings.json (Azure Function App Settings)

    {
      "RSS_FEED_URL": "https://yle.fi/rss/uutiset/paauutiset",
      "AZURE_STORAGE_CONNECTION_STRING": "DefaultEndpointsProtocol=https;AccountName=...",
      "STORAGE_CONTAINER": "finnish-news-tools",
      "ADD_ORIGIN_RSS": "true",
      "SCRAPER_CONFIG_PATH": "scraper-config.yaml",
      "AZURE_STORAGE_TABLE_CONNECTION_STRING": "DefaultEndpointsProtocol=https;AccountName=...",
      "RATE_LIMIT_TABLE_NAME": "rateLimits",
      "RSS_PARSER_DAILY_LIMIT": "50",
      "ARTICLE_SCRAPER_DAILY_LIMIT": "50",
      "CACHE_TTL_HOURS": "1"
    }

---

## Implementation Details

### Function 1: RSS Feed Parser

Pseudocode:

    function main(request):
        check authentication
        if auth failed:
            return 401 error
        
        check rate limit
        if limit exceeded:
            return 429 error with count and limit
        
        get force_reload parameter from request (default: false)
        get cache TTL from config (default: 1 hour)
        cleanup expired cache entries in cache/yle/
        
        if not force_reload:
            check cache for paauutiset.json
            if cache hit and valid (expires_at > now):
                return full cached feed data (with items array)
        
        get RSS URL from request params or config
        parse RSS feed using feedparser
        extract feed metadata and items
        add ?origin=rss to article links if configured
        extract shortcode from each article URL
        
        calculate expires_at = now + TTL hours
        save JSON to blob storage at cache/yle/paauutiset.json with expires_at
        increment rate limit counter
        return full feed data (with items array)

### Function 2: Article Scraper

Pseudocode:

    function main(request):
        check authentication
        if auth failed:
            return 401 error
        
        check rate limit
        if limit exceeded:
            return 429 error with count and limit
        
        get cache TTL from config (default: 1 hour)
        cleanup expired cache entries in cache/yle/articles/
        
        load scraping config from YAML
        parse request body to get URLs list
        
        for each URL:
            extract shortcode from URL
            check cache for {shortcode}_{lang}.json
            if cache hit and valid (expires_at > now):
                return cached data
            
            add ?origin=rss if configured
            fetch HTML with requests
            parse HTML with BeautifulSoup
            remove excluded elements per config
            extract title using config selectors
            extract paragraphs using config selectors
            apply cleaning rules (min length, strip whitespace)
            
            calculate expires_at = now + TTL hours
            save JSON to blob storage at cache/yle/articles/{shortcode}_{lang}.json with expires_at
        
        increment rate limit counter
        return results list with status per URL

---

## Authentication Implementation

### Shared Auth Module

Pseudocode:

    function validateToken(request):
        token = get token from Authorization header or X-Token header
        issued_date = get issued_date from X-Issued-Date header
        username = get username from X-Username header
        if not token or not issued_date or not username:
            return false
        
        validate token using shared token validator with username
        if token invalid or expired:
            return false
        return true
    
    function validateRequest(request):
        if not validateToken(request):
            return 401 error with message "Authentication required"
        return true

## Cache Cleanup Implementation

### Shared Cache Cleaner Module

All Azure Functions use shared cache cleanup code that runs before each RSS feed load or article load. This ensures expired cache entries are cleared automatically and prevents accumulation of old data.

Location: azure-one/scraper-one/functions/shared/cache_cleaner.py

Pseudocode:

    class CacheCleaner:
        init(blob_service, container_name):
            store blob service and container client
        
        cleanup_expired(cache_path, ttl_hours):
            list all blobs in cache_path
            cleaned_count = 0
            for each blob:
                try load cache JSON
                if cache has expires_at:
                    if expires_at < now:
                        delete blob
                        cleaned_count += 1
                else:
                    check blob last_modified
                    if last_modified + ttl_hours < now:
                        delete blob
                        cleaned_count += 1
            return cleaned_count
        
        check_cache_valid(blob_path, ttl_hours):
            if blob exists:
                load cache JSON
                if cache has expires_at:
                    return expires_at > now
                else:
                    check blob last_modified
                    return last_modified + ttl_hours > now
            return false

Usage pattern in functions:

    cache_cleaner = CacheCleaner(blob_service, container_name)
    cache_cleaner.cleanup_expired("cache/yle/", ttl_hours=1)
    if cache_cleaner.check_cache_valid("cache/yle/paauutiset.json", ttl_hours=1):
        return cached_data

## Rate Limiting Implementation

### Shared Rate Limiter Module

Pseudocode:

    class DailyRateLimiter:
        init(connection_string, table_name):
            connect to Azure Table Storage
            create table if not exists
        
        check_limit(function_name, daily_limit):
            get today's date key (YYYY-MM-DD)
            get row key: function_name_date
            try get entity from table
            if exists and count >= limit:
                return false
            return true
        
        get_daily_count(function_name):
            get row key: function_name_date
            try get entity from table
            return request_count or 0
        
        increment(function_name):
            get row key: function_name_date
            try get existing entity
            if exists:
                increment request_count
                update entity
            else:
                create new entity with count=1

### Function: Query Daily Request Counts

Pseudocode:

    function main(request):
        get function_name from query params (optional)
        get daily limits from config
        
        if function_name specified:
            get count for that function
            return count, limit, remaining, percentage
        else:
            get counts for all functions
            return counts for rss_feed_parser and article_scraper

---

## Dependencies (requirements.txt)

    azure-functions>=1.18.0
    azure-storage-blob>=12.19.0
    azure-data-tables>=12.4.0
    feedparser>=6.0.10
    beautifulsoup4>=4.12.0
    lxml>=5.1.0
    requests>=2.31.0
    pyyaml>=6.0.1

---

## Deployment Steps

1. Create Azure Function App

    az functionapp create \
      --name finnish-news-scraper \
      --resource-group rg-finnish-news \
      --consumption-plan-location westeurope \
      --runtime python \
      --runtime-version 3.11

2. Configure Application Settings

    az functionapp config appsettings set \
      --name finnish-news-scraper \
      --resource-group rg-finnish-news \
      --settings \
        RSS_FEED_URL="https://yle.fi/rss/uutiset/paauutiset" \
        AZURE_STORAGE_CONNECTION_STRING="..." \
        STORAGE_CONTAINER="finnish-news-tools" \
        ADD_ORIGIN_RSS="true" \
        AZURE_STORAGE_TABLE_CONNECTION_STRING="..." \
        RATE_LIMIT_TABLE_NAME="rateLimits" \
        RSS_PARSER_DAILY_LIMIT="50" \
        ARTICLE_SCRAPER_DAILY_LIMIT="50" \
        CACHE_TTL_HOURS="1"

3. Deploy Functions

    cd azure-one/scraper-one/functions
    func azure functionapp publish finnish-news-scraper

4. Upload Config File

    # Upload scraper-config.yaml to function app
    az functionapp deployment source config-zip \
      --name finnish-news-scraper \
      --resource-group rg-finnish-news \
      --src scraper-config.zip

---

## Testing

### Test RSS Feed Parser

First authenticate to get token:

    curl -X POST "https://finnish-news-auth.azurewebsites.net/api/authenticate" \
      -H "Content-Type: application/json" \
      -d '{"password": "{password}"}'

Then use token:

    curl -X GET "https://finnish-news-scraper.azurewebsites.net/api/rss-feed-parser" \
      -H "X-Token: {token_from_auth_response}" \
      -H "X-Issued-Date: {issued_date_from_auth_response}" \
      -H "X-Username: {username_from_auth_response}"

### Test Article Scraper

    curl -X POST "https://finnish-news-scraper.azurewebsites.net/api/article-scraper" \
      -H "Content-Type: application/json" \
      -H "X-Token: {token}" \
      -H "X-Issued-Date: {issued_date}" \
      -H "X-Username: {username}" \
      -d '{
        "urls": ["https://yle.fi/a/74-20197424"],
        "add_origin_rss": true,
        "language_code": "fi"
      }'

### Query Daily Request Counts

    curl -X GET "https://finnish-news-scraper.azurewebsites.net/api/query-rate-limits" \
      -H "X-Token: {token}" \
      -H "X-Issued-Date: {issued_date}" \
      -H "X-Username: {username}"

    # Query specific function
    curl -X GET "https://finnish-news-scraper.azurewebsites.net/api/query-rate-limits?function_name=rss_feed_parser" \
      -H "X-Token: {token}" \
      -H "X-Issued-Date: {issued_date}" \
      -H "X-Username: {username}"

---

## Integration Workflow

1. RSS Feed Parser runs (timer or manual trigger)
2. Saves paauutiset.json to blob storage at cache/yle/paauutiset.json
3. Article Scraper reads paauutiset.json (or receives URLs via HTTP)
4. Scrapes each article URL
5. Saves article files to blob storage at cache/yle/articles/{shortcode}_{language_code}.json
6. Articles ready for translation pipeline

---

## Error Handling

- Authentication: Return 401 if token missing, invalid, or expired
- RSS Parser: Retry on network errors, validate RSS format
- Article Scraper: Skip failed articles, log errors, continue processing
- Storage: Handle blob upload failures gracefully
- Config: Fallback to default selectors if YAML parsing fails
- Rate Limiting: Return 429 with current count and limit when exceeded

---

## Monitoring

- Track RSS feed fetch success rate
- Monitor article scraping success rate
- Log failed URLs for manual review
- Track storage usage and costs
- Monitor daily request counts via /api/query-rate-limits endpoint
- Alert when rate limits approach threshold (e.g., >80% of daily limit)
- Track rate limit violations (429 responses)
- Track authentication failures (401 responses) for security monitoring

---

## Next Steps

1. Create function app structure
2. Implement RSS feed parser function
3. Implement article scraper function
4. Create YAML config file with parsing rules
5. Add shared storage client utilities
6. Test locally with Azure Functions Core Tools
7. Deploy to Azure
8. Set up monitoring and alerts
