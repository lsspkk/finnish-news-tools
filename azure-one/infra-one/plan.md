# Azure Deployment Architecture Plan

## Executive Summary

Deploy Finnish News Tools as a web application on Azure with minimal cost, leveraging Azure's free tiers and cost-effective services. The architecture separates backend (API + scraping/translation) from frontend (static site), uses Azure AD B2C for authentication, and Azure Translator for translation services.

---

## Architecture Overview

    ┌─────────────────────────────────────────────────────────────────┐
    │                         USER BROWSER                            │
    │  ┌──────────────────────────────────────────────────────────┐   │
    │  │  Static Website (Azure Static Web Apps - FREE)           │   │
    │  │  - React/Vue/Plain HTML                                  │   │
    │  │  - Language switching UI                                 │   │
    │  │  - Article display                                       │   │
    │  │  - Token stored in localStorage (persists across sessions)│   │
    │  └──────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────┘
                                  │
                                  │ HTTPS (Auth + API Calls)
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │              Azure AD B2C (FREE for <50k MAU)                   │
    │              - Email/Password authentication                     │
    │              - Google OAuth integration                          │
    │              - User management                                   │
    └─────────────────────────────────────────────────────────────────┘
                                  │
                                  │ JWT Token
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │         Azure Functions (Consumption Plan - Pay-per-use)        │
    │  ┌──────────────────────────────────────────────────────────┐   │
    │  │  Backend API                                             │   │
    │  │  - /api/scrape (trigger scraping job)                    │   │
    │  │  - /api/translate (trigger translation)                  │   │
    │  │  - /api/articles (get articles list)                     │   │
    │  │  - /api/article/{id} (get specific article)              │   │
    │  │  - JWT validation                                        │   │
    │  │  - Per-user rate limiting (in-memory or Redis)           │   │
    │  └──────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                      Azure Services                             │
    │                                                                 │
    │  ┌─────────────────────┐  ┌─────────────────────────────────┐  │
    │  │ Azure Translator    │  │ Azure Blob Storage (Hot)        │  │
    │  │ - 2M chars/month    │  │ - articles.html                 │  │
    │  │ - F0 Free tier      │  │ - scraped content               │  │
    │  └─────────────────────┘  │ - translation cache             │  │
    │                           │ - LRS (cheapest replication)    │  │
    │  ┌─────────────────────┐  └─────────────────────────────────┘  │
    │  │ Azure Table Storage │                                        │
    │  │ - User rate limits  │                                        │
    │  │ - Article metadata  │                                        │
    │  └─────────────────────┘                                        │
    └─────────────────────────────────────────────────────────────────┘

---

## Decision Matrix: Authentication Strategy

### Option 1: Azure AD B2C (RECOMMENDED)

Pros:
- FREE tier: 50,000 MAU (Monthly Active Users)
- Built-in email/password authentication
- Google OAuth integration (and other social providers)
- Industry-standard security
- JWT tokens for API authentication
- User management UI included
- Integrates seamlessly with Azure Functions

Cons:
- Initial setup complexity (30-60 min)
- Overkill for very small user base (<5 users)

Cost: $0/month for <50k MAU

### Option 2: No Authentication + Direct API Key

Pros:
- Zero setup time
- Simplest implementation

Cons:
- API key exposed in frontend code
- Anyone can extract and abuse your Azure Translator quota
- No user tracking or rate limiting
- Security risk

Cost: $0/month but HIGH RISK of quota exhaustion

### Option 3: Backend API Key Only (No User Auth)

Pros:
- Simple implementation
- API key hidden from frontend
- Can implement IP-based rate limiting

Cons:
- No user tracking
- Limited rate limiting options (IP can be spoofed)
- No multi-user support

Cost: $0/month

### RECOMMENDATION: Option 1 (Azure AD B2C)

Rationale:
1. Your use case needs rate limiting PER USER due to Azure Translator's 2M character limit
2. Free tier covers most small-to-medium projects
3. Proper authentication enables fair quota distribution
4. Enables future features (user preferences, saved articles, etc.)
5. Minimal cost even if you exceed 50k MAU ($0.0055 per MAU)

---

## Cost Analysis

### Monthly Costs (Estimated)

| Service                  | Tier        | Cost             | Usage Assumption          |
|--------------------------|-------------|------------------|---------------------------|
| Azure Static Web Apps    | Free        | $0               | <100GB bandwidth          |
| Azure Functions          | Consumption | $0-5             | <1M requests, <400k GB-s  |
| Azure AD B2C             | Free/Pay    | $0               | <50k MAU                  |
| Azure Translator         | F0 Free     | $0               | <2M chars/month           |
| Azure Blob Storage       | Hot LRS     | $1-3             | ~10GB storage, minimal ops|
| Azure Table Storage      | Standard    | $0.50            | Rate limit tracking       |
| TOTAL                    |             | $1.50-$8.50/month|                           |

### Cost Optimization Tips
- Use Azure Translator F0 tier (2M chars/month free)
- Enable translation caching to reduce API calls (short TTL prevents long-term storage)
- Use Azure Functions Consumption plan (1M free requests)
- Store static assets in Blob Storage (cheaper than App Service)
- Use Azure Table Storage instead of Cosmos DB (100x cheaper)
- Automatic cache cleanup reduces storage costs

---

## Cache Strategy and TTL

### Purpose

Caches are short-term storage to make text translation feasible, not for copying or archiving news content. All cached data has configurable TTL (Time To Live) and is automatically cleaned up.

### Cache TTL Configuration

- RSS feed cache: Configurable TTL (default: 1 hour)
- Article cache: Configurable TTL (default: 1 hour)
- Translation cache: Configurable TTL (default: 24 hours)

All caches include expires_at timestamps and are automatically cleaned up before each operation.

### Shared Cache Cleanup Pattern

Before each RSS feed load or article load, Azure Functions check the cache and clear all expired data:

    function cleanup_expired_cache(cache_path, ttl_hours):
        list all blobs in cache_path
        for each blob:
            load cache metadata
            if expires_at < now:
                delete blob
        return cleaned_count

This ensures no old data accumulates and prevents long-term copying of news content.

### Cache Clearing Function

A dedicated Azure Function can be created to clear all caches after a specified period (e.g., 1 hour):

    function clear_all_caches():
        cleanup_expired_cache("cache/yle/", ttl=1)
        cleanup_expired_cache("cache/translations/", ttl=1)
        return success

This function can be triggered manually or via timer to ensure no news content is stored for extended periods.

---

## Storage Strategy for Scraper Results

### Option A: Azure Blob Storage (RECOMMENDED)

Structure:

    container: scraped-content
    ├── responses/
    │   ├── 2025-12-17T10-30-00/
    │   │   ├── articles.html
    │   │   ├── articles/
    │   │   │   ├── article-001.html
    │   │   │   └── article-002.html
    │   │   └── downloads/
    │   │       └── ...
    │   └── 2025-12-17T15-45-00/
    │       └── ...
    ├── cache/
    │   ├── yle/
    │   │   ├── paauutiset.json (TTL: 1 hour)
    │   │   └── articles/
    │   │       └── {shortcode}_{lang}.json (TTL: 1 hour)
    │   └── translations/
    │       └── {article_id}/{source_lang}_{target_lang}.json (TTL: 24 hours)

Implementation:

    from azure.storage.blob import BlobServiceClient
    
    # Upload scraped content
    blob_service = BlobServiceClient.from_connection_string(conn_str)
    container = blob_service.get_container_client("scraped-content")
    
    # Save articles.html
    blob_client = container.get_blob_client(f"responses/{timestamp}/articles.html")
    blob_client.upload_blob(html_content, overwrite=True)

Pros:
- Cheap storage ($0.018/GB/month for Hot tier)
- Unlimited scale
- Built-in versioning and lifecycle management
- Direct HTTPS access
- CDN integration possible

Cons:
- Not a file system (requires code changes)

### Option B: Azure Files (SMB share)

Pros:
- Acts like local file system
- Minimal code changes

Cons:
- More expensive ($0.06/GB/month)
- Lower performance for random access

### Option C: Local Storage (Dev Only)

Pros:
- No code changes
- No cost

Cons:
- Not suitable for Azure Functions (ephemeral)
- No persistence across deployments

### RECOMMENDATION: Azure Blob Storage

Modify scraper to use Azure SDK for blob operations.

---

## Rate Limiting Strategy

### Per-User Rate Limiting

Since Azure Translator has 2M chars/month limit, implement:

    from datetime import datetime, timedelta
    from azure.data.tables import TableServiceClient
    
    class RateLimiter:
        def __init__(self, table_client):
            self.table = table_client
        
        def check_limit(self, user_id: str, chars: int) -> bool:
            """Check if user is within monthly limit"""
            month_key = datetime.utcnow().strftime("%Y-%m")
            entity_key = f"{user_id}_{month_key}"
            
            try:
                entity = self.table.get_entity(
                    partition_key="rate_limits",
                    row_key=entity_key
                )
                current_usage = entity.get("char_count", 0)
            except:
                current_usage = 0
            
            # Allocate quota per user (example: 50k chars/user/month)
            user_limit = 50000
            
            if current_usage + chars > user_limit:
                return False
            
            # Update usage
            self.table.upsert_entity({
                "PartitionKey": "rate_limits",
                "RowKey": entity_key,
                "char_count": current_usage + chars,
                "last_updated": datetime.utcnow()
            })
            
            return True

### Quota Allocation Strategy

- Small user base (10 users): 200k chars/user/month = 2M total
- Medium user base (50 users): 40k chars/user/month
- Large user base (200 users): 10k chars/user/month

Consider implementing:
- User tier system (free vs paid)
- Daily limits to prevent burst usage
- Caching to reduce API calls

---

## Code Changes Required

### 1. Scraper Modifications

File: scraper/scraper2.py

Changes:

    # Add Azure Blob Storage support
    from azure.storage.blob import BlobServiceClient
    import os
    
    class AzureBlobStorage:
        def __init__(self):
            self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            self.blob_service = BlobServiceClient.from_connection_string(
                self.connection_string
            )
            self.container_name = "scraped-content"
        
        def save_file(self, blob_path: str, content: bytes):
            """Save file to Azure Blob Storage"""
            container = self.blob_service.get_container_client(self.container_name)
            blob_client = container.get_blob_client(blob_path)
            blob_client.upload_blob(content, overwrite=True)
        
        def read_file(self, blob_path: str) -> bytes:
            """Read file from Azure Blob Storage"""
            container = self.blob_service.get_container_client(self.container_name)
            blob_client = container.get_blob_client(blob_path)
            return blob_client.download_blob().readall()
        
        def list_files(self, prefix: str) -> list:
            """List files in container"""
            container = self.blob_service.get_container_client(self.container_name)
            return [blob.name for blob in container.list_blobs(name_starts_with=prefix)]
    
    # Replace file operations with blob operations
    storage = AzureBlobStorage()
    storage.save_file(f"responses/{timestamp}/articles.html", html_content)

### 2. Translator Modifications

File: translator/translate_news.py

Changes:
- Replace local cache files with Azure Blob Storage
- Add rate limiting check before translation
- Update file paths to use blob storage

### 3. Create Backend API (Azure Functions)

New file: backend/functions/articles/__init__.py

    import azure.functions as func
    import json
    from azure.storage.blob import BlobServiceClient
    import logging
    
    def main(req: func.HttpRequest) -> func.HttpResponse:
        logging.info('Articles API triggered')
        
        # Validate JWT token
        auth_header = req.headers.get('Authorization')
        if not auth_header or not validate_jwt(auth_header):
            return func.HttpResponse(
                "Unauthorized",
                status_code=401
            )
        
        # Get user from token
        user_id = get_user_from_token(auth_header)
        
        # List available articles
        storage = BlobServiceClient.from_connection_string(
            os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        )
        
        container = storage.get_container_client("scraped-content")
        
        # Find all articles.html files
        articles = []
        for blob in container.list_blobs(name_starts_with="responses/"):
            if blob.name.endswith("articles.html"):
                articles.append({
                    "timestamp": blob.name.split("/")[1],
                    "url": f"/api/article/{blob.name.split('/')[1]}"
                })
        
        return func.HttpResponse(
            json.dumps(articles),
            mimetype="application/json",
            status_code=200
        )

### 4. Create Frontend

See static-site-one/plan.md for detailed frontend implementation.

Frontend uses localStorage (not sessionStorage) to store authentication tokens. This allows tokens to persist across browser sessions. If backend rejects token, frontend redirects to login for re-authentication.

Key frontend features:
- Token-based authentication (username/password)
- localStorage for token persistence
- Responsive design (mobile/tablet/desktop/wide)
- On-demand article loading and translation

---

## Deployment Steps

### Phase 1: Azure Setup (30 min)

1. Create Azure Account

    az login

2. Create Resource Group

    az group create --name {resource-group} --location {location}

3. Create Storage Account

    az storage account create \
      --name {storage-account} \
      --resource-group {resource-group} \
      --location {location} \
      --sku Standard_LRS
    
    # Create container
    az storage container create \
      --name {container-name} \
      --account-name {storage-account}

4. Create Azure Translator

    az cognitiveservices account create \
      --name {translator-name} \
      --resource-group {resource-group} \
      --kind TextTranslation \
      --sku F0 \
      --location {location}
    
    # Get key
    az cognitiveservices account keys list \
      --name {translator-name} \
      --resource-group {resource-group}

5. Create Azure AD B2C Tenant
   - Go to Azure Portal → Create Resource → Azure AD B2C
   - Follow wizard (takes 5-10 min)
   - Configure user flows (Sign up/Sign in)
   - Add Google identity provider (optional)

### Phase 2: Code Deployment (1 hour)

1. Deploy Azure Functions

    cd backend
    func init --python
    func azure functionapp publish {function-app-name}

2. Deploy Static Web App

    cd frontend
    az staticwebapp create \
      --name {static-web-app-name} \
      --resource-group {resource-group} \
      --source . \
      --location {location} \
      --branch main \
      --app-location "/" \
      --output-location "dist"

3. Configure Environment Variables

    az functionapp config appsettings set \
      --name {function-app-name} \
      --resource-group {resource-group} \
      --settings \
        AZURE_STORAGE_CONNECTION_STRING="..." \
        AZURE_TRANSLATOR_KEY="..." \
        AZURE_B2C_TENANT="..." \
        AZURE_B2C_CLIENT_ID="..."

### Phase 3: Testing (30 min)

1. Test authentication flow
2. Test scraping job
3. Test translation
4. Test rate limiting
5. Verify costs in Azure Cost Management

---

## Security Considerations

1. API Key Protection
   - Store Azure Translator key in Azure Key Vault
   - Use managed identities for Azure Functions
   - Never commit keys to Git

2. Authentication
   - Use HTTPS only
   - Validate JWT tokens on every request
   - Implement CORS properly

3. Rate Limiting
   - Implement per-user quotas
   - Add IP-based throttling for abuse prevention
   - Monitor usage patterns

4. Data Privacy
   - Don't store user passwords (handled by Azure AD B2C)
   - Encrypt data at rest (default in Azure)
   - Implement data retention policies

---

## Cache Clearing Function

A dedicated Azure Function can be created to clear all caches after a specified period (e.g., 1 hour) to ensure no news content is stored for extended periods:

Pseudocode:

    function clear_all_caches(request):
        check authentication
        if auth failed:
            return 401 error
        
        get cache TTL from config (default: 1 hour)
        cleaned_rss = cleanup_expired_cache("cache/yle/", ttl=1)
        cleaned_articles = cleanup_expired_cache("cache/yle/articles/", ttl=1)
        cleaned_translations = cleanup_expired_cache("cache/translations/", ttl=1)
        
        return {
            "cleaned_rss": cleaned_rss,
            "cleaned_articles": cleaned_articles,
            "cleaned_translations": cleaned_translations,
            "total_cleaned": cleaned_rss + cleaned_articles + cleaned_translations
        }

This function can be triggered manually or via timer trigger to ensure no news content is stored for extended periods.

---

## Monitoring & Maintenance

### Metrics to Track
- Azure Translator character usage (daily/monthly)
- Per-user translation quota consumption
- API response times
- Error rates
- Storage growth
- Cache cleanup statistics (entries cleaned per operation)

### Alerts to Configure
- Azure Translator usage >80% of quota
- Function execution failures >5%
- Storage costs >$10/month
- Authentication failures spike

### Azure Application Insights

    # Enable Application Insights
    az monitor app-insights component create \
      --app {app-insights-name} \
      --location {location} \
      --resource-group {resource-group}

---

## Translator Quota Monitoring Feature

### Overview

API endpoint and frontend UI to monitor Azure Translator quota usage. Shows total characters translated, available quota, remaining quota, and when quota resets.

### Architecture

    Frontend (Static Site)
    └── Calls /api/translator-quota
        └── Azure Function: translator_quota
            ├── Query Azure Monitor Metrics API
            ├── Get TextCharactersTranslated metric (current month)
            ├── Get quota limit from config (2M chars/month for F0 tier)
            ├── Calculate next reset time (monthly billing cycle)
            └── Return usage statistics

### Backend API: translator_quota

New Azure Function endpoint: /api/translator-quota

Purpose:
- Get total characters translated in current billing period
- Get available monthly quota limit
- Calculate remaining quota
- Determine next quota reset time

Authentication:
- Requires valid token (same as other endpoints)

Implementation:

    function main(request):
        check authentication
        if auth failed:
            return 401 error
        
        get Azure Translator resource ID from config
        get quota limit from config (default: 2000000 for F0 tier)
        
        calculate billing period start (first day of current month)
        calculate billing period end (now)
        
        query Azure Monitor Metrics API:
            metric: TextCharactersTranslated
            start_time: billing period start
            end_time: billing period end
            aggregation: Total
        
        total_chars = sum of metric values
        
        calculate next reset:
            next_month = current month + 1
            next_reset = first day of next month at 00:00:00 UTC
        
        remaining = quota_limit - total_chars
        percentage_used = (total_chars / quota_limit) * 100
        
        return {
            total_characters_translated: total_chars,
            quota_limit: quota_limit,
            remaining_quota: remaining,
            percentage_used: percentage_used,
            billing_period_start: billing_period_start,
            billing_period_end: billing_period_end,
            next_reset_time: next_reset,
            next_reset_date: next_reset formatted as ISO 8601
        }

Azure Monitor Metrics API:

Uses Azure Monitor REST API or Python SDK (azure-mgmt-monitor).

Authentication:
- Use managed identity (recommended) or service principal
- Function App needs Monitoring Reader role on Translator resource

Pseudocode:

    from azure.identity import DefaultAzureCredential
    from azure.monitor.query import MetricsQueryClient
    
    credential = DefaultAzureCredential()
    client = MetricsQueryClient(credential)
    
    resource_id = "/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.CognitiveServices/accounts/{name}"
    
    start_time = first_day_of_current_month()
    end_time = datetime.now()
    
    response = client.query_resource(
        resource_id,
        metric_names=["TextCharactersTranslated"],
        start_time=start_time,
        end_time=end_time,
        aggregation="Total"
    )
    
    total_chars = sum metric values from response

Configuration:

Add to Function App settings:

    AZURE_TRANSLATOR_RESOURCE_ID=/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.CognitiveServices/accounts/{name}
    AZURE_TRANSLATOR_QUOTA_LIMIT=2000000
    AZURE_TRANSLATOR_BILLING_CYCLE_START_DAY=1

Note: Quota resets monthly on billing cycle. For F0 tier, typically resets on 1st of each month. Can be configured if different.

### Frontend Integration

Display quota usage in UI (header or settings page).

Pseudocode:

    function loadQuotaInfo():
        authHeaders = getAuthHeaders()
        response = fetch(translatorApiUrl + "/translator-quota", {
            headers: authHeaders
        })
        quotaData = response.json()
        displayQuotaInfo(quotaData)
    
    function displayQuotaInfo(data):
        show "Characters translated: {data.total_characters_translated} / {data.quota_limit}"
        show "Remaining: {data.remaining_quota} ({100 - data.percentage_used}%)"
        show "Next reset: {formatDate(data.next_reset_date)}"
        
        if data.percentage_used > 80:
            show warning style
        if data.percentage_used > 95:
            show error style

UI Location:
- Option 1: Header widget (always visible)
- Option 2: Settings/info page
- Option 3: Tooltip on translation button

Recommended: Small info widget in header showing percentage used, with full details on click.

### Error Handling

- Azure Monitor API errors: Return error message, log warning
- Missing resource ID: Return 500 error
- Authentication errors: Return 401
- Rate limit API errors: Cache result for 1 hour to reduce API calls

### Cost Considerations

- Azure Monitor Metrics API: Free (included in Azure subscription)
- Function execution: Pay per call (minimal cost)
- No additional storage needed

### Testing

    curl -X GET "https://{function-app-name}.azurewebsites.net/api/translator-quota" \
      -H "X-Token: {token}" \
      -H "X-Issued-Date: {issued_date}" \
      -H "X-Username: {username}"

Expected Response:

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

---

## Alternative: Simpler No-Auth MVP

If you want to start without authentication for MVP:

1. Skip Azure AD B2C
2. Use single backend API key
3. Implement IP-based rate limiting only
4. Add authentication later

Pros: Faster to deploy (30 min instead of 2 hours)
Cons: Risk of quota exhaustion, no user tracking

Decision: Start simple, add auth when you have >10 users or hit rate limits.

---

## Next Steps

1. Choose authentication strategy (Recommendation: Azure AD B2C)
2. Set up Azure resources (use deployment steps above)
3. Modify scraper/translator to use Blob Storage
4. Deploy consolidated backend API (azure-one/functions/)
5. Build simple frontend for article viewing
6. Test and iterate

Note: All functions are now in single Function App at azure-one/functions/

---

## Questions & Answers

Q: What if I exceed 2M characters/month?
A: Upgrade to S1 tier ($10/1M chars). Alternatively, implement stricter per-user quotas or add payment tier.

Q: Can I use local storage for development?
A: Yes, use environment variable to switch between local and blob storage.

Q: How do I backup scraped data?
A: Enable Azure Blob Storage versioning and lifecycle management to move old data to Archive tier ($0.002/GB/month).

Q: What about Playwright in Azure Functions?
A: Azure Functions may timeout (5 min default). Consider:
- Use Premium plan (longer timeout, ~$150/month)
- Use Azure Container Instances for scraping (~$5/month)
- Use external service (ScrapingBee, ScraperAPI)

---

## Conclusion

Recommended Architecture:
- Azure Static Web Apps (frontend)
- Azure Functions (backend API)
- Azure AD B2C (authentication with Google OAuth)
- Azure Blob Storage (scraped content)
- Azure Translator F0 (2M chars/month free)
- Per-user rate limiting (50k chars/user/month)
- Total cost: $1.50-8.50/month

This architecture is:
- Cheap: Uses free tiers extensively
- Scalable: Can handle 100s of users
- Secure: Industry-standard authentication
- Maintainable: Separate concerns (frontend/backend)
- Production-ready: Built on Azure's reliable infrastructure
