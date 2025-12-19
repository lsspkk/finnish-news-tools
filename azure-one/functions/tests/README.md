# Functions Tests

Test scripts for the consolidated Azure Functions.

## Setup

Before running tests, ensure local settings are configured:

    cd azure-one/functions
    cp local.settings.json.template local.settings.json.local
    cp scraper-config.yaml.template scraper-config.yaml.local

Edit local.settings.json.local and scraper-config.yaml.local with your local configuration.

Default password for testing: Hello world!

## Test Scripts

### 1. Basic Test (test_scraper.py)

Runs authentication, RSS feed parser, and article scraper.

### 2. Cache-Aware Test (test_cache_aware.py)

Checks cache/storage status first, then fetches RSS feed or articles only if they're not already cached.

### 3. Translator Quota Test (test_translator_quota.py)

Tests the translator quota endpoint with mocked Azure Monitor API. Can also test with real Azure Monitor API if configured.

## Usage

### Basic Test

Run the basic test script:

    cd azure-one/functions
    source ../../venv/bin/activate
    python tests/test_scraper.py

When prompted:
- Username: any value (e.g., test_user)
- Password: Hello world! (required, authentication will fail with wrong password)

### Cache-Aware Test

Run the cache-aware test script:

    cd azure-one/functions
    source ../../venv/bin/activate
    python tests/test_cache_aware.py

When prompted:
- Username: any value (e.g., test_user)
- Password: Hello world! (required, authentication will fail with wrong password)

### Translator Quota Test

**Setup for real Azure Monitor testing (optional but recommended):**

    cd azure-one/functions
    ./tests/setup-local-monitor-test.sh [resource-group] [translator-name]

This will configure Azure credentials and resource ID automatically.

**Run the test:**

    cd azure-one/functions
    source ../../venv/bin/activate
    python tests/test_translator_quota.py

When prompted:
- Username: any value (e.g., test_user)
- Password: Hello world! (required, authentication will fail with wrong password)

This test:
1. Tests with real Azure Monitor API (if AZURE_TRANSLATOR_RESOURCE_ID is configured)
2. Falls back to mocked Azure Monitor API if real API is not configured

See `tests/TEST_TRANSLATOR_QUOTA.md` for detailed setup instructions.

### Testing with Running Function App (curl)

If you have the function app running locally (`func start`), you can test with curl:

    cd azure-one/functions
    ./tests/test_translator_quota_curl.sh

Or with custom parameters:

    ./tests/test_translator_quota_curl.sh http://localhost:7071 username "password"

This script:
1. Authenticates and gets a token
2. Calls the translator-quota endpoint
3. Shows the response in JSON format

## What the tests do

### Basic Test (test_scraper.py)

1. Authentication: Prompts for username and password, validates against authenticate function
2. RSS Feed Parser: Fetches and parses the RSS feed from Yle
3. Article Scraper: Scrapes the first article from the RSS feed
4. Output: Prints all results in pretty JSON format

### Cache-Aware Test (test_cache_aware.py)

1. Cache Status Check: Logs current cache/storage situation (RSS feed and articles)
2. Conditional RSS Fetch: Fetches RSS feed only if not already cached
3. Conditional Article Fetch: Scrapes article only if not already cached
4. Final Status: Shows final cache status after operations
5. Output: Prints results in pretty JSON format

Note: The cache-aware test checks if paauutiset.json or articles exist before fetching, avoiding unnecessary API calls.

### Translator Quota Test (test_translator_quota.py)

1. Authentication: Prompts for username and password
2. Mocked Test: Tests with mocked Azure Monitor API response (always works)
3. Real Test: Tests with real Azure Monitor API if AZURE_TRANSLATOR_RESOURCE_ID is configured
4. Output: Prints quota usage statistics in JSON format

Note: For real Azure Monitor API testing, you need:
- AZURE_TRANSLATOR_RESOURCE_ID environment variable set
- Azure credentials configured (DefaultAzureCredential)
- Function App needs Monitoring Reader role on Translator resource

## Authentication

Tests use the real authenticate function:
- Password validation: Only Hello world! is accepted (from template)
- Wrong password: Authentication fails with 401 error
- Token generation: Uses shared token_validator for consistency

## Requirements

- Python 3.8+
- All dependencies from requirements.txt
- Local settings configured
