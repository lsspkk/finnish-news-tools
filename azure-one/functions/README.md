# Consolidated Azure Functions

Single Function App containing all backend functions for Finnish News Tools.

## Structure

```
functions/
├── authenticate/              # User authentication
├── rss_feed_parser/          # RSS feed parsing
├── article_scraper/          # Article content scraping
├── translate_article/        # Article translation (stub)
├── query_rate_limits/        # Rate limit queries
├── shared/                   # Shared utilities
│   ├── token_validator.py
│   ├── rate_limiter.py
│   ├── storage_factory.py
│   ├── cache_cleaner.py
│   └── local_storage.py
├── tests/                    # Test scripts
├── host.json                 # Function App configuration
├── requirements.txt          # Python dependencies
├── local.settings.json.template
└── scraper-config.yaml.template
```

## Functions

### authenticate
HTTP trigger for user authentication. Returns token for API access.

### rss_feed_parser
HTTP trigger for parsing RSS feeds. Caches results for 24h.

### article_scraper
HTTP trigger for scraping article content. Caches results for 24h.

### translate_article
HTTP trigger for translating articles (stub, not yet implemented).

### query_rate_limits
HTTP trigger for querying daily rate limit usage.

## Local Development

1. Copy template files:

    cp local.settings.json.template local.settings.json.local
    cp scraper-config.yaml.template scraper-config.yaml.local

2. Configure local settings in `local.settings.json.local`

3. Run locally:

    func start

## Production Authentication

For production deployment, use month-based password authentication:

1. Copy template:

    cp authenticate/__init__.py.local.template authenticate/__init__.py.local

2. The file authenticate/__init__.py.local is in .gitignore and will not be committed

3. Deployment scripts automatically use __init__.py.local for production

4. Password changes each month (e.g., "December" for December 2025)

The template file (__init__.py.local.template) is in git, but the actual file (__init__.py.local) is not committed for security.

## Deployment

Deploy from infra-one folder:

    cd ../infra-one
    ./deploy-3-deploy-functions.sh

Or manually:

    func azure functionapp publish <FUNCTION_APP_NAME>

## Configuration

All configuration via environment variables in `local.settings.json` (local) or Azure Function App settings (production).

Key settings:
- `USE_LOCAL_STORAGE`: Use local file storage instead of Azure
- `AUTH_SECRET`: Secret for token generation
- `STORAGE_CONTAINER`: Azure Blob Storage container name
- `RATE_LIMIT_TABLE_NAME`: Azure Table Storage table for rate limits
- Daily limits: `RSS_PARSER_DAILY_LIMIT`, `ARTICLE_SCRAPER_DAILY_LIMIT`, `TRANSLATION_DAILY_LIMIT`

## Testing

See `tests/README.md` for test instructions.

## Shared Code

All functions share common utilities:
- Token validation and generation
- Rate limiting (daily and IP-based)
- Storage abstraction (Azure Blob/Table or local)
- Cache management
