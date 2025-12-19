# Local Development Plan

## Overview

Plan for running Azure Functions locally during development. Uses local file storage instead of Azure Blob Storage and Azure Table Storage. Includes testing setup for each function.

Key features:
- Run functions locally with Azure Functions Core Tools
- Local file storage for blob storage replacement
- Local file storage for table storage replacement
- Test each function independently
- No Azure account required for development

---

## Local Storage Structure

### Blob Storage Replacement

Local filesystem structure mirrors Azure Blob Storage:

    local-dev/
    ├── storage/
    │   └── finnish-news-tools/
    │       ├── cache/
    │       │   ├── yle/
    │       │   │   ├── paauutiset.json
    │       │   │   └── articles/
    │       │   │       ├── 74-20197424_fi.json
    │       │   │       └── 74-20199829_fi.json
    │       │   └── translations/
    │       │       └── 74-20197424/
    │       │           └── fi_en.json
    │       └── responses/
    │           └── 2025-12-18T10-30-00/
    │               └── articles.html

### Table Storage Replacement

Local JSON files for rate limits:

    local-dev/
    ├── tables/
    │   └── rateLimits.json
    │       {
    │         "rate_limits": {
    │           "rss_feed_parser_2025-12-18": {
    │             "PartitionKey": "rate_limits",
    │             "RowKey": "rss_feed_parser_2025-12-18",
    │             "function_name": "rss_feed_parser",
    │             "date": "2025-12-18",
    │             "request_count": 5,
    │             "created_at": "2025-12-18T09:00:00Z",
    │             "last_updated": "2025-12-18T10:30:00Z"
    │           }
    │         }
    │       }

---

## Local Storage Client

### Shared Local Storage Module

File: shared/local_storage.py

Pseudocode:

    class LocalBlobStorage:
        def __init__(self, base_path):
            self.base_path = Path(base_path)
            self.base_path.mkdir(parents=True, exist_ok=True)
        
        def save_file(self, blob_path, content):
            file_path = self.base_path / blob_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, dict):
                with open(file_path, 'w') as f:
                    json.dump(content, f, indent=2)
            else:
                with open(file_path, 'wb') as f:
                    f.write(content)
        
        def read_file(self, blob_path):
            file_path = self.base_path / blob_path
            if not file_path.exists():
                return None
            if file_path.suffix == '.json':
                with open(file_path, 'r') as f:
                    return json.load(f)
            else:
                with open(file_path, 'rb') as f:
                    return f.read()
        
        def file_exists(self, blob_path):
            file_path = self.base_path / blob_path
            return file_path.exists()
        
        def list_files(self, prefix):
            prefix_path = self.base_path / prefix
            if not prefix_path.exists():
                return []
            files = []
            for file_path in prefix_path.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(self.base_path)
                    files.append(str(relative_path))
            return files

    class LocalTableStorage:
        def __init__(self, table_file_path):
            self.table_file_path = Path(table_file_path)
            self.table_file_path.parent.mkdir(parents=True, exist_ok=True)
            self._load_table()
        
        def _load_table(self):
            if self.table_file_path.exists():
                with open(self.table_file_path, 'r') as f:
                    self.data = json.load(f)
            else:
                self.data = {}
        
        def _save_table(self):
            with open(self.table_file_path, 'w') as f:
                json.dump(self.data, f, indent=2)
        
        def get_entity(self, partition_key, row_key):
            table_name = self.table_file_path.stem
            if table_name not in self.data:
                return None
            if partition_key not in self.data[table_name]:
                return None
            return self.data[table_name][partition_key].get(row_key)
        
        def create_entity(self, entity):
            table_name = self.table_file_path.stem
            partition_key = entity['PartitionKey']
            row_key = entity['RowKey']
            
            if table_name not in self.data:
                self.data[table_name] = {}
            if partition_key not in self.data[table_name]:
                self.data[table_name][partition_key] = {}
            
            self.data[table_name][partition_key][row_key] = entity
            self._save_table()
        
        def update_entity(self, entity):
            self.create_entity(entity)

---

## Environment Configuration

### Local Settings File

File: local.settings.json (for Azure Functions Core Tools)

    {
      "IsEncrypted": false,
      "Values": {
        "AzureWebJobsStorage": "UseDevelopmentStorage=true",
        "FUNCTIONS_WORKER_RUNTIME": "python",
        "USE_LOCAL_STORAGE": "true",
        "LOCAL_STORAGE_PATH": "./local-dev/storage",
        "LOCAL_TABLES_PATH": "./local-dev/tables",
        "RSS_FEED_URL": "https://yle.fi/rss/uutiset/paauutiset",
        "STORAGE_CONTAINER": "finnish-news-tools",
        "RSS_PARSER_DAILY_LIMIT": "50",
        "ARTICLE_SCRAPER_DAILY_LIMIT": "50",
        "TRANSLATION_DAILY_LIMIT": "50",
        "TRANSLATION_CACHE_TTL_HOURS": "24",
        "AZURE_TRANSLATOR_KEY": "test-key",
        "AZURE_TRANSLATOR_ENDPOINT": "https://api.cognitive.microsofttranslator.com/",
        "AZURE_TRANSLATOR_REGION": "westeurope",
        "AUTH_SECRET": "local-dev-secret-key"
      }
    }

---

## Storage Client Factory

### Storage Client Selection

File: shared/storage_factory.py

Pseudocode:

    def get_blob_storage():
        use_local = os.getenv('USE_LOCAL_STORAGE', 'false').lower() == 'true'
        if use_local:
            base_path = os.getenv('LOCAL_STORAGE_PATH', './local-dev/storage')
            return LocalBlobStorage(base_path)
        else:
            connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
            return BlobServiceClient.from_connection_string(connection_string)
    
    def get_table_storage(table_name):
        use_local = os.getenv('USE_LOCAL_STORAGE', 'false').lower() == 'true'
        if use_local:
            tables_path = os.getenv('LOCAL_TABLES_PATH', './local-dev/tables')
            table_file = Path(tables_path) / f"{table_name}.json"
            return LocalTableStorage(table_file)
        else:
            connection_string = os.getenv('AZURE_STORAGE_TABLE_CONNECTION_STRING')
            return TableServiceClient.from_connection_string(connection_string)

---

## Testing Setup

### Test Structure

    azure-one/
    ├── tests/
    │   ├── __init__.py
    │   ├── conftest.py              # Pytest fixtures
    │   ├── test_rss_feed_parser.py
    │   ├── test_article_scraper.py
    │   ├── test_translate_article.py
    │   ├── test_authenticate.py
    │   └── test_rate_limiter.py
    ├── test_fixtures/
    │   ├── sample_rss_feed.xml
    │   ├── sample_article.html
    │   └── sample_article_data.json

### Pytest Configuration

File: pytest.ini

    [pytest]
    testpaths = tests
    python_files = test_*.py
    python_classes = Test*
    python_functions = test_*
    env =
        USE_LOCAL_STORAGE=true
        LOCAL_STORAGE_PATH=./test-storage
        LOCAL_TABLES_PATH=./test-tables

### Test Fixtures

File: tests/conftest.py

Pseudocode:

    @pytest.fixture
    def local_storage(tmp_path):
        storage_path = tmp_path / "storage"
        return LocalBlobStorage(storage_path)
    
    @pytest.fixture
    def local_table(tmp_path):
        table_path = tmp_path / "rateLimits.json"
        return LocalTableStorage(table_path)
    
    @pytest.fixture
    def sample_rss_feed():
        with open('test_fixtures/sample_rss_feed.xml', 'r') as f:
            return f.read()
    
    @pytest.fixture
    def sample_article_html():
        with open('test_fixtures/sample_article.html', 'r') as f:
            return f.read()

---

## Function Tests

### Test RSS Feed Parser

File: tests/test_rss_feed_parser.py

Pseudocode:

    def test_rss_feed_parser_success(local_storage, sample_rss_feed):
        # Mock feedparser to return sample feed
        # Call function
        # Verify JSON saved to local storage
        # Verify structure matches expected format
    
    def test_rss_feed_parser_rate_limit(local_table):
        # Set up rate limit exceeded
        # Call function
        # Verify 429 response
    
    def test_rss_feed_parser_auth_failure():
        # Call without token
        # Verify 401 response

### Test Article Scraper

File: tests/test_article_scraper.py

Pseudocode:

    def test_article_scraper_success(local_storage, sample_article_html):
        # Mock requests.get to return sample HTML
        # Call function with URL
        # Verify article JSON saved to local storage
        # Verify title and paragraphs extracted
    
    def test_article_scraper_multiple_urls(local_storage):
        # Call with multiple URLs
        # Verify all articles saved
        # Verify results list returned

### Test Translate Article

File: tests/test_translate_article.py

Pseudocode:

    def test_translate_article_cache_hit(local_storage):
        # Set up cached translation
        # Call function
        # Verify cached translation returned
        # Verify no API call made
    
    def test_translate_article_cache_miss(local_storage):
        # Mock Azure Translator API
        # Call function
        # Verify translation saved to cache
        # Verify translation returned

### Test Authenticate

File: tests/test_authenticate.py

Pseudocode:

    def test_authenticate_success():
        # Call with valid password (current month)
        # Verify token returned
        # Verify username included
        # Verify expiration date set
    
    def test_authenticate_failure():
        # Call with invalid password
        # Verify 401 response

### Test Rate Limiter

File: tests/test_rate_limiter.py

Pseudocode:

    def test_rate_limiter_check_limit(local_table):
        # Set up rate limit
        # Check limit
        # Verify within limit returns true
    
    def test_rate_limiter_increment(local_table):
        # Increment counter
        # Verify count increased
        # Verify file updated

---

## Running Functions Locally

### Prerequisites

    Install Azure Functions Core Tools
    Install Python dependencies
    Set USE_LOCAL_STORAGE=true

### Start Functions Locally

    cd azure-one/functions
    func start

Functions available at:
- http://localhost:7071/api/authenticate
- http://localhost:7071/api/rss-feed-parser
- http://localhost:7071/api/article-scraper
- http://localhost:7071/api/translate-article
- http://localhost:7071/api/query-rate-limits

### Test Function Locally

    curl -X GET "http://localhost:7071/api/rss-feed-parser" \
      -H "X-Token: {token}" \
      -H "X-Issued-Date: {date}" \
      -H "X-Username: {username}"

---

## Development Workflow

1. Set USE_LOCAL_STORAGE=true in local.settings.json
2. Start functions locally: func start
3. Run tests: pytest
4. Check local storage files in local-dev/ directory
5. Test functions with curl or Postman
6. When ready, deploy to Azure

---

## Local Storage Cleanup

### Cleanup Script

File: scripts/clean_local_storage.py

Pseudocode:

    def clean_local_storage():
        storage_path = Path('./local-dev/storage')
        tables_path = Path('./local-dev/tables')
        
        if storage_path.exists():
            shutil.rmtree(storage_path)
        if tables_path.exists():
            shutil.rmtree(tables_path)
        
        print("Local storage cleaned")

Run before tests or when needed.

---

## Benefits

- No Azure account needed for development
- Fast iteration (no network calls)
- Easy to test edge cases
- Can inspect local files directly
- Works offline
- Easy to reset state (delete local files)

---

## Migration to Azure

When deploying to Azure:
1. Set USE_LOCAL_STORAGE=false
2. Set Azure connection strings
3. Functions automatically use Azure services
4. No code changes needed

---

## File Structure

    azure-one/
    ├── local-dev-plan.md
    ├── functions/            # Consolidated Function App
    │   ├── authenticate/
    │   ├── rss_feed_parser/
    │   ├── article_scraper/
    │   ├── translate_article/
    │   ├── query_rate_limits/
    │   ├── shared/
    │   │   ├── storage_factory.py
    │   │   └── local_storage.py
    │   ├── tests/
    │   └── local.settings.json.template
    └── local-dev/
        ├── storage/          # Local blob storage
        └── tables/           # Local table storage

---

## Notes

- Local storage mimics Azure structure
- JSON files for easy inspection
- Tests use temporary directories
- Can switch between local and Azure easily
- All functions work the same way
