# Azure Functions Plan: On-Demand Article Translation

## Overview

Azure Functions for translating Finnish news articles on-demand from a static website. Users click a language button to translate the currently opened article, with translations cached in Azure Blob Storage for 24 hours (customizable).

Key features:
- On-demand translation (one language at a time)
- Azure Blob Storage cache with TTL
- Automatic cache cleanup (old entries cleared)
- Works with static site frontend
- Reuses existing Azure Translator implementation

---

## Architecture

    Static Website (Azure Static Web Apps)
    └── User clicks language button
        └── JavaScript calls /api/translate-article
            └── Azure Function: translate_article
                ├── Check cache in Azure Blob Storage
                ├── If cache hit and valid (< 24h): return cached translation
                ├── If cache miss or expired: call Azure Translator API
                ├── Save translation to cache
                └── Return translation to frontend

---

## Function: translate_article

### Purpose
- Translate article paragraphs to target language on-demand
- Use Azure Blob Storage cache with TTL
- Clear expired cache entries automatically
- Enforce daily request rate limits

### Trigger
- HTTP Trigger (POST) - called from frontend JavaScript

### Rate Limiting
- Daily request limit: 50 requests per day (configurable)
- Tracked in Azure Table Storage
- Returns 429 Too Many Requests when limit exceeded
- Request count resets at midnight UTC

### Input
Request body:

    {
        "article_id": "74-20197424",
        "source_lang": "fi",
        "target_lang": "en",
        "paragraphs": [
            "First paragraph text...",
            "Second paragraph text...",
            "Third paragraph text..."
        ]
    }

### Output
Response body:

    {
        "article_id": "74-20197424",
        "source_lang": "fi",
        "target_lang": "en",
        "translations": [
            "First paragraph translated...",
            "Second paragraph translated...",
            "Third paragraph translated..."
        ],
        "cache_hit": true,
        "cached_at": "2025-12-18T09:51:22Z",
        "translated_at": "2025-12-18T09:51:22Z"
    }

### Cache Structure

Azure Blob Storage path:

    finnish-news-tools/cache/translations/{article_id}/{source_lang}_{target_lang}.json

Cache file format:

    {
        "article_id": "74-20197424",
        "source_lang": "fi",
        "target_lang": "en",
        "paragraphs": [
            "First paragraph text...",
            "Second paragraph text..."
        ],
        "translations": [
            "First paragraph translated...",
            "Second paragraph translated..."
        ],
        "created_at": "2025-12-18T09:51:22Z",
        "expires_at": "2025-12-19T09:51:22Z",
        "cache_ttl_hours": 24
    }

### Cache TTL Logic

- Default TTL: 24 hours (customizable via TRANSLATION_CACHE_TTL_HOURS config)
- Cache key: article_id + source_lang + target_lang + paragraph hash
- Before each translation request: cleanup expired cache entries automatically
- Cache validation: check expires_at timestamp
- Purpose: Short-term cache for translation feasibility, not for copying news content

---

## Implementation Details

### Function Structure

    azure-one/translator-one/functions/
    ├── translate_article/
    │   ├── __init__.py              # Main function entry point
    │   ├── translator.py            # Azure Translator wrapper
    │   ├── cache_manager.py         # Blob Storage cache with TTL
    │   └── utils.py                 # Helper functions
    ├── query_rate_limits/
    │   └── __init__.py              # Query daily request counts
    ├── shared/
    │   ├── token_validator.py       # Token validation
    │   ├── rate_limiter.py          # Daily request rate limiter
    │   ├── storage_client.py        # Shared Azure Blob Storage client
    │   └── config.py                # Configuration loader
    └── translator-config.yaml       # Translation configuration

### Function: translate_article

Pseudocode:

    function main(request):
        check authentication
        if auth failed:
            return 401 error
        
        check rate limit
        if limit exceeded:
            return 429 error with count and limit
        
        parse request body (article_id, source_lang, target_lang, paragraphs)
        validate required fields
        
        get cache TTL from config (default 24h)
        create cache manager
        
        cleanup expired cache entries before checking
        check cache for article_id/source_lang_target_lang
        if cache hit and valid (expires_at > now):
            return cached translations
        
        if cache miss:
            initialize Azure Translator
            translate each paragraph
            calculate expires_at = now + TTL hours
            save translations to cache with expires_at
            increment rate limit counter
            return translations

### Cache Manager

Pseudocode:

    class TranslationCacheManager:
        init(blob_service, container_name, cache_ttl_hours):
            store blob service and container client
        
        get(cache_key, paragraphs):
            get blob path: cache/translations/{cache_key}.json
            if blob exists:
                load cache data
                check expires_at timestamp
                if expired:
                    return None
                check paragraph hash matches
                if hash mismatch:
                    return None
                return cache data
            return None
        
        save(cache_key, paragraphs, translations, source_lang, target_lang):
            calculate expires_at = now + TTL hours
            generate paragraph hash
            create cache data with metadata
            save JSON to blob storage
        
        cleanup_expired():
            list all blobs in cache/translations/
            cleaned_count = 0
            for each blob:
                try load cache data
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

### Translator Wrapper

Pseudocode:

    class AzureTranslatorWrapper:
        init(subscription_key, endpoint, region, source_lang, target_lang):
            create AzureTranslator instance
        
        translate(text):
            if text empty:
                return text
            call Azure Translator API
            return translated text

### Storage Client

Pseudocode:

    function get_blob_service_client():
        get AZURE_STORAGE_CONNECTION_STRING from env
        return BlobServiceClient from connection string

### Authentication

Functions validate session tokens from auth function, not passwords directly.

Pseudocode:

    function validateToken(request):
        token = get token from Authorization header or X-Token header
        issued_date = get issued_date from X-Issued-Date header
        username = get username from X-Username header
        if not token or not issued_date or not username:
            return false
        
        validate token using shared token validator
        if token invalid or expired:
            return false
        return true
    
    function validateRequest(request):
        if not validateToken(request):
            return 401 error with message "Authentication required"
        return true

### Rate Limiter

Pseudocode:

    class DailyRateLimiter:
        init(connection_string, table_name):
            connect to Azure Table Storage
            create table if not exists
        
        check_limit(function_name, daily_limit):
            get today's date key
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

### Query Rate Limits Function

Pseudocode:

    function main(request):
        check authentication
        if auth failed:
            return 401 error
        
        get function_name from query params (default: translate_article)
        get daily_limit from config
        get daily count for function_name
        return count, limit, remaining, percentage_used

---

## Frontend Integration

### JavaScript Example

    async function translateArticle(articleId, targetLang) {
        const articleElement = document.querySelector(`[data-article-id="${articleId}"]`);
        const paragraphs = Array.from(articleElement.querySelectorAll('p'))
            .map(p => p.textContent.trim())
            .filter(text => text.length > 0);
        
        try {
            const response = await fetch('/api/translate-article', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    article_id: articleId,
                    source_lang: 'fi',
                    target_lang: targetLang,
                    paragraphs: paragraphs
                })
            });
            
            const data = await response.json();
            
            if (data.translations) {
                displayTranslations(articleElement, data.translations, targetLang);
            }
        } catch (error) {
            console.error('Translation error:', error);
        }
    }
    
    function displayTranslations(articleElement, translations, targetLang) {
        const paragraphs = articleElement.querySelectorAll('p');
        
        paragraphs.forEach((para, index) => {
            if (translations[index]) {
                const translationDiv = document.createElement('div');
                translationDiv.className = `translation translation-${targetLang}`;
                translationDiv.setAttribute('data-lang', targetLang);
                translationDiv.textContent = translations[index];
                para.insertAdjacentElement('afterend', translationDiv);
            }
        });
    }

---

## Configuration

### Function App Settings

    {
        "AZURE_STORAGE_CONNECTION_STRING": "DefaultEndpointsProtocol=https;AccountName=...",
        "STORAGE_CONTAINER": "finnish-news-tools",
        "AZURE_TRANSLATOR_KEY": "...",
        "AZURE_TRANSLATOR_ENDPOINT": "https://api.cognitive.microsofttranslator.com/",
        "AZURE_TRANSLATOR_REGION": "westeurope",
        "TRANSLATION_CACHE_TTL_HOURS": "24",
        "AZURE_STORAGE_TABLE_CONNECTION_STRING": "DefaultEndpointsProtocol=https;AccountName=...",
        "RATE_LIMIT_TABLE_NAME": "rateLimits",
        "TRANSLATION_DAILY_LIMIT": "50",
        "TRANSLATION_CACHE_TTL_HOURS": "24"
    }

### translator-config.yaml (Optional)

    translation:
        cache:
            ttl_hours: 24
            cleanup_on_request: true
        azure:
            endpoint: "https://api.cognitive.microsofttranslator.com/"
            region: "westeurope"
            timeout: 30
            max_retries: 3

---

## Dependencies (requirements.txt)

    azure-functions>=1.18.0
    azure-storage-blob>=12.19.0
    azure-data-tables>=12.4.0
    requests>=2.31.0

Note: translators package should be copied to function app or installed as dependency.

---

## Deployment Steps

1. Create Azure Function App

    az functionapp create \
      --name finnish-news-translator \
      --resource-group rg-finnish-news \
      --consumption-plan-location westeurope \
      --runtime python \
      --runtime-version 3.11

2. Configure Application Settings

    az functionapp config appsettings set \
      --name finnish-news-translator \
      --resource-group rg-finnish-news \
      --settings \
        AZURE_STORAGE_CONNECTION_STRING="..." \
        STORAGE_CONTAINER="finnish-news-tools" \
        AZURE_TRANSLATOR_KEY="..." \
        AZURE_TRANSLATOR_ENDPOINT="https://api.cognitive.microsofttranslator.com/" \
        AZURE_TRANSLATOR_REGION="westeurope" \
        TRANSLATION_CACHE_TTL_HOURS="24" \
        AZURE_STORAGE_TABLE_CONNECTION_STRING="..." \
        RATE_LIMIT_TABLE_NAME="rateLimits" \
        TRANSLATION_DAILY_LIMIT="50" \
        TRANSLATION_CACHE_TTL_HOURS="24"

3. Copy translators package

    Copy translator/translators/ directory to function app.

4. Deploy Functions

    cd azure-one/translator-one/functions
    func azure functionapp publish finnish-news-translator

---

## Testing

### Test Translation Function

First authenticate to get token:

    curl -X POST "https://finnish-news-auth.azurewebsites.net/api/authenticate" \
      -H "Content-Type: application/json" \
      -d '{"password": "{password}"}'

Then use token:

    curl -X POST "https://finnish-news-translator.azurewebsites.net/api/translate-article" \
      -H "Content-Type: application/json" \
      -H "X-Token: {token_from_auth_response}" \
      -H "X-Issued-Date: {issued_date_from_auth_response}" \
      -H "X-Username: {username_from_auth_response}" \
      -d '{
        "article_id": "74-20197424",
        "source_lang": "fi",
        "target_lang": "en",
        "paragraphs": [
          "Tämä on ensimmäinen kappale.",
          "Tämä on toinen kappale."
        ]
      }'

### Expected Response

    {
      "article_id": "74-20197424",
      "source_lang": "fi",
      "target_lang": "en",
      "translations": [
        "This is the first paragraph.",
        "This is the second paragraph."
      ],
      "cache_hit": false,
      "translated_at": "2025-12-18T09:51:22Z"
    }

### Query Daily Request Counts

    curl -X GET "https://finnish-news-translator.azurewebsites.net/api/query-rate-limits" \
      -H "X-Token: {token}" \
      -H "X-Issued-Date: {issued_date}" \
      -H "X-Username: {username}"

    # Response
    {
      "date": "2025-12-18",
      "function_name": "translate_article",
      "request_count": 23,
      "daily_limit": 50,
      "remaining": 27,
      "percentage_used": 46.0
    }

---

## Cost Considerations

- Azure Functions Consumption Plan: Pay per execution
- Azure Blob Storage: ~$0.018/GB/month for cache files
- Azure Translator: 2M chars/month free (F0 tier)
- Cache reduces API calls significantly

Cost optimization:
- Use cache TTL to balance freshness vs API calls
- Cleanup expired cache to reduce storage costs
- Monitor Azure Translator usage via Azure Portal

---

## Error Handling

- Authentication: Return 401 if token missing, invalid, or expired
- Network errors: Retry with exponential backoff
- Azure Translator rate limits: Return error to frontend, let user retry
- Cache errors: Log warning, continue without cache
- Invalid requests: Return 400 with error message
- Rate limiting: Return 429 with current count and limit when exceeded

---

## Monitoring

- Track translation requests per language
- Monitor cache hit rate
- Track Azure Translator API usage
- Monitor function execution time
- Alert on high error rates
- Monitor daily request counts via /api/query-rate-limits endpoint
- Alert when rate limits approach threshold (e.g., >80% of daily limit)
- Track rate limit violations (429 responses)
- Track authentication failures (401 responses) for security monitoring

---

## Function: translator_quota

### Purpose

Get Azure Translator quota usage statistics including total characters translated, quota limit, remaining quota, and next reset time.

### Trigger

HTTP Trigger (GET) - called from frontend JavaScript

### Authentication

Requires valid token (same as other endpoints)

### Input

No request body. Query parameters optional (none required).

### Output

Response body:

    {
        "total_characters_translated": 1250000,
        "quota_limit": 2000000,
        "remaining_quota": 750000,
        "percentage_used": 62.5,
        "billing_period_start": "2025-12-01T00:00:00Z",
        "billing_period_end": "2025-12-18T10:30:00Z",
        "next_reset_time": "2026-01-01T00:00:00Z",
        "next_reset_date": "2026-01-01T00:00:00Z"
    }

### Implementation

Pseudocode:

    function main(request):
        check authentication
        if auth failed:
            return 401 error
        
        get AZURE_TRANSLATOR_RESOURCE_ID from env
        get AZURE_TRANSLATOR_QUOTA_LIMIT from env (default: 2000000)
        get AZURE_TRANSLATOR_BILLING_CYCLE_START_DAY from env (default: 1)
        
        now = datetime.now(timezone.utc)
        billing_start = first_day_of_current_month(now, start_day)
        billing_end = now
        
        credential = DefaultAzureCredential()
        metrics_client = MetricsQueryClient(credential)
        
        try:
            response = metrics_client.query_resource(
                resource_id=AZURE_TRANSLATOR_RESOURCE_ID,
                metric_names=["TextCharactersTranslated"],
                start_time=billing_start,
                end_time=billing_end,
                aggregation="Total"
            )
            
            total_chars = 0
            for metric in response.metrics:
                for time_series in metric.timeseries:
                    for point in time_series.data:
                        if point.total:
                            total_chars += point.total
        except Exception as e:
            log error
            return 500 error with message
        
        next_reset = first_day_of_next_month(now, start_day)
        remaining = quota_limit - total_chars
        percentage = (total_chars / quota_limit) * 100
        
        return {
            total_characters_translated: total_chars,
            quota_limit: quota_limit,
            remaining_quota: max(0, remaining),
            percentage_used: round(percentage, 2),
            billing_period_start: billing_start.isoformat(),
            billing_period_end: billing_end.isoformat(),
            next_reset_time: next_reset.isoformat(),
            next_reset_date: next_reset.isoformat()
        }

### Azure Monitor Integration

Uses Azure Monitor Metrics API to query TextCharactersTranslated metric.

Authentication:
- Use DefaultAzureCredential (supports managed identity)
- Function App needs Monitoring Reader role on Translator resource

Dependencies:

    azure-identity>=1.15.0
    azure-monitor-query>=1.2.0

### Configuration

Add to Function App settings:

    AZURE_TRANSLATOR_RESOURCE_ID=/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.CognitiveServices/accounts/{name}
    AZURE_TRANSLATOR_QUOTA_LIMIT=2000000
    AZURE_TRANSLATOR_BILLING_CYCLE_START_DAY=1

### Error Handling

- Azure Monitor API errors: Return 500 with error message, log warning
- Missing resource ID: Return 500 error
- Authentication errors: Return 401
- Invalid quota limit: Use default 2000000

### Testing

    curl -X GET "https://finnish-news-translator.azurewebsites.net/api/translator-quota" \
      -H "X-Token: {token}" \
      -H "X-Issued-Date: {issued_date}" \
      -H "X-Username: {username}"

---

## Next Steps

1. Create function app structure
2. Implement translate_article function
3. Implement cache manager with TTL
4. Copy translators package to function app
5. Create shared storage client
6. Test locally with Azure Functions Core Tools
7. Deploy to Azure
8. Integrate with frontend static site
9. Set up monitoring and alerts
