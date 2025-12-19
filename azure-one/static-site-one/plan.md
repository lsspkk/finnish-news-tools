# Static Website Plan: Finnish News Reader

## Overview

Simple static website for reading and translating Finnish news articles. Uses plain HTML/CSS/JavaScript for minimal complexity. Features token-based authentication and on-demand article loading with translation.

Key features:
- Token-based authentication (username/password)
- Load RSS feed JSON from Azure Blob Storage
- Display article list with links
- Load article content in Finnish
- On-demand translation to selected languages
- Configurable language options

---

## Architecture

    User Browser
    └── Static Website (Azure Static Web Apps)
        ├── Login page (authentication)
        ├── Article list page
        │   └── Loads RSS feed JSON from blob storage
        └── Article detail page
            ├── YLE link (external)
            ├── Näytä button (load Finnish text)
            └── Language buttons (load translations)

---

## File Structure

    azure-one/static-site-one/
    ├── index.html              # Login page
    ├── articles.html          # Article list page
    ├── article.html           # Article detail page
    ├── config.js              # Configuration (languages, API endpoints)
    ├── auth.js                # Authentication logic
    ├── api.js                 # API client functions
    ├── styles.css             # Responsive styling (mobile/tablet/desktop/wide)
    └── app.js                 # Main application logic

---

## Authentication

Frontend authenticates with username and password to get session token, then uses token for API calls. Username is displayed in UI.

Tokens are stored in localStorage for persistence across browser sessions. If backend responds with authentication error, frontend redirects to login page for new authentication.

Pseudocode:

    function login():
        username = get username from user input
        password = get password from user input
        response = call /api/authenticate with username and password
        if response.success:
            token = response.token
            username = response.username
            issued_at = response.issued_at
            save token, username, and issued_at to localStorage
            display username in header
            redirect to articles page
        else:
            show error message
    
    function getAuthHeaders():
        token = get from localStorage
        username = get from localStorage
        issued_at = get issued_at from localStorage
        if not token or not username or not issued_at:
            redirect to login
        return {
            "X-Token": token,
            "X-Issued-Date": issued_at,
            "X-Username": username
        }
    
    function getUsername():
        return get username from localStorage

---

## Configuration

File: config.js

    const CONFIG = {
        authApiUrl: "https://{function-app-name}.azurewebsites.net/api",
        apiBaseUrl: "https://{function-app-name}.azurewebsites.net/api",
        translatorApiUrl: "https://{function-app-name}.azurewebsites.net/api",
        storageContainer: "{storage-container}",
        rssFeedPath: "cache/yle/paauutiset.json",
        articlePath: "cache/yle/articles",
        languages: [
            { code: "en", name: "English" },
            { code: "sv", name: "Svenska" },
            { code: "de", name: "Deutsch" },
            { code: "es", name: "Español" },
            { code: "zh", name: "中文" }
        ],
        sourceLanguage: "fi"
    }

---

## Pages

### 1. Login Page (index.html)

Pseudocode:

    function renderLoginPage():
        check if already authenticated
        if authenticated:
            redirect to articles.html
        
        show username input field
        show password input field
        show login button
        on login button click:
            get username and password from inputs
            call authenticate API with username and password
            if authentication successful:
                save token and username to localStorage
                redirect to articles.html
            else:
                show error message

### 2. Article List Page (articles.html)

Pseudocode:

    function renderHeader():
        username = getUsername()
        show username in header
        show logout button (clears localStorage and redirects to login)
        quotaWidget = renderQuotaWidget()
        if quotaWidget:
            add quotaWidget to header
    
    function loadRSSFeed():
        authHeaders = getAuthHeaders()
        url = apiBaseUrl + "/rss-feed-parser"
        fetch JSON from API with authHeaders
        parse feed data
        display feed metadata (title, RSS load date)
        format RSS load date as: "Ladattu klo HH:MM - DD.MM.YYYY"
        check if RSS feed is 8+ hours old
        if old, show gray "Päivitä" button next to date
        display article list:
            for each article:
                show title
                show publication date
                show categories
                show link to article.html?shortcode={shortcode}
    
    function forceReloadRSS():
        authHeaders = getAuthHeaders()
        url = apiBaseUrl + "/rss-feed-parser?force_reload=true"
        fetch JSON from API with authHeaders
        reload articles list with fresh data
        update RSS load date display

    function renderArticleList():
        check authentication
        if not authenticated:
            redirect to index.html
        
        renderHeader()
        call loadRSSFeed()
        display articles in list format
        each article links to article.html with shortcode parameter

### 3. Article Detail Page (article.html)

Pseudocode:

    function renderHeader():
        username = getUsername()
        show username in header
        show back button to articles list
        show logout button
    
    function loadArticle(shortcode):
        authHeaders = getAuthHeaders()
        url = apiBaseUrl + "/article-scraper"
        body = { urls: ["https://yle.fi/a/" + shortcode], language_code: "fi" }
        fetch JSON from API with authHeaders
        return article data (title, paragraphs)

    function displayArticle(articleData):
        show article title
        show YLE link (external link to yle.fi article)
        show Näytä button
        on Näytä button click:
            if article not loaded:
                call loadArticle(shortcode)
                display paragraphs in Finnish
            toggle paragraph visibility

    function translateArticle(shortcode, targetLang):
        get article data (already loaded)
        extract paragraphs
        authHeaders = getAuthHeaders()
        call translate API:
            POST /api/translate-article
            headers: authHeaders
            body: { article_id, source_lang, target_lang, paragraphs }
        display translations below Finnish paragraphs
        toggle translation visibility on button click

    function renderArticlePage():
        check authentication
        if not authenticated:
            redirect to index.html
        
        renderHeader()
        get shortcode from URL parameter
        show article header
        show YLE link
        show Näytä button
        show language buttons (from config)
        on language button click:
            call translateArticle(shortcode, language_code)
            show/hide translations for that language

---

## API Integration

All API calls require X-Token header with session token from authentication.

### Authentication Helper

Pseudocode:

    function authenticate(username, password):
        url = authApiUrl + "/authenticate"
        response = fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: username, password: password })
        })
        return response.json()
    
    function getAuthHeaders():
        token = get from localStorage
        username = get from localStorage
        issued_at = get issued_at from localStorage
        if not token or not username or not issued_at:
            redirect to login
        return {
            "X-Token": token,
            "X-Issued-Date": issued_at,
            "X-Username": username
        }

### Load RSS Feed

Pseudocode:

    function fetchRSSFeed(forceReload = false):
        authHeaders = getAuthHeaders()
        url = apiBaseUrl + "/rss-feed-parser"
        if forceReload:
            url += "?force_reload=true"
        response = fetch(url, {
            headers: authHeaders
        })
        return response.json()

Note: Calls Azure Function which requires authentication token. Function returns full RSS feed JSON with items array. If force_reload=true, bypasses cache and fetches fresh data.

### Load Article

Pseudocode:

    function fetchArticle(shortcode, lang):
        authHeaders = getAuthHeaders()
        url = apiBaseUrl + "/article-scraper"
        body = {
            urls: ["https://yle.fi/a/" + shortcode],
            language_code: lang
        }
        response = fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...authHeaders
            },
            body: JSON.stringify(body)
        })
        return response.json()

Note: Calls Azure Function to scrape article if not already cached, or can fetch directly from blob storage if public access enabled.

### Translate Article

Pseudocode:

    function translateArticle(articleId, sourceLang, targetLang, paragraphs):
        authHeaders = getAuthHeaders()
        url = translatorApiUrl + "/translate-article"
        body = {
            article_id: articleId,
            source_lang: sourceLang,
            target_lang: targetLang,
            paragraphs: paragraphs
        }
        response = fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...authHeaders
            },
            body: JSON.stringify(body)
        })
        return response.json()

### Get Translator Quota

Pseudocode:

    function fetchTranslatorQuota():
        authHeaders = getAuthHeaders()
        url = translatorApiUrl + "/translator-quota"
        response = fetch(url, {
            method: "GET",
            headers: authHeaders
        })
        return response.json()

Note: Returns quota usage statistics including total characters translated, quota limit, remaining quota, percentage used, and next reset time.

---

## UI Flow

1. User visits site
2. Check authentication status
3. If not authenticated, show login page with username and password fields
4. User enters username (any value) and password
5. Frontend calls /api/authenticate with username and password
6. If correct, frontend receives token and username, saves to localStorage
7. Redirect to articles page
8. Articles page shows username in header
9. Articles page loads RSS feed JSON using token
10. Articles page loads translator quota info and displays in header
11. User sees list of articles
12. User clicks article link
13. Article page shows:
    - Header with username and logout button
    - Translator quota info widget (optional)
    - Article title
    - YLE link (external)
    - Näytä button
    - Language buttons
14. User clicks Näytä button
15. Finnish text loads and displays
16. User clicks language button (e.g., "English")
17. Translation loads and displays below Finnish text
18. User can toggle translations on/off

---

## Translator Quota Display

### Purpose

Display Azure Translator quota usage information to users so they can monitor usage and know when quota resets.

### UI Component

Quota info widget displayed in header (articles page and article page).

Pseudocode:

    function renderQuotaWidget():
        quotaData = loadQuotaInfo()
        if not quotaData:
            return
        
        widget = create div with class "quota-widget"
        
        percentage = quotaData.percentage_used
        remaining = quotaData.remaining_quota
        nextReset = formatDate(quotaData.next_reset_date)
        
        if percentage > 95:
            widget.className += " quota-critical"
        else if percentage > 80:
            widget.className += " quota-warning"
        
        widget.innerHTML = `
            <span class="quota-label">Quota:</span>
            <span class="quota-value">${percentage.toFixed(1)}%</span>
            <span class="quota-details">(${formatNumber(remaining)} remaining)</span>
            <span class="quota-reset">Reset: ${nextReset}</span>
        `
        
        add click handler to show full details modal
        
        return widget
    
    function loadQuotaInfo():
        try:
            quotaData = fetchTranslatorQuota()
            cache quotaData in memory for 5 minutes
            return quotaData
        catch error:
            log error
            return null
    
    function formatDate(isoDate):
        date = new Date(isoDate)
        return date.toLocaleDateString() + " " + date.toLocaleTimeString()
    
    function formatNumber(num):
        if num >= 1000000:
            return (num / 1000000).toFixed(1) + "M"
        else if num >= 1000:
            return (num / 1000).toFixed(1) + "k"
        return num.toString()

### Display Options

Option 1: Compact header widget (recommended)
- Shows percentage used and remaining
- Click to expand full details
- Color coded: green (<80%), yellow (80-95%), red (>95%)

Option 2: Full details always visible
- Shows all information: used/total, remaining, percentage, next reset
- Takes more space but always visible

Option 3: Tooltip on translation button
- Shows quota info when hovering over translation button
- Less intrusive but requires hover

Recommended: Option 1 - compact widget with expandable details.

### Styling

Pseudocode:

    .quota-widget {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        cursor: pointer;
    }
    
    .quota-widget.quota-warning {
        background-color: #fff3cd;
        color: #856404;
    }
    
    .quota-widget.quota-critical {
        background-color: #f8d7da;
        color: #721c24;
    }
    
    .quota-label {
        font-weight: bold;
    }
    
    .quota-value {
        font-weight: bold;
    }
    
    .quota-details {
        color: #666;
    }
    
    .quota-reset {
        font-size: 11px;
        color: #999;
    }

### Error Handling

- API errors: Hide widget or show "Quota info unavailable"
- Network errors: Use cached data if available
- Authentication errors: Hide widget (will redirect to login)

### Caching

Cache quota data in memory for 5 minutes to reduce API calls. Refresh on page load or manual refresh button.

---

## Styling

Responsive CSS for mobile, tablet, desktop, and wide displays:

### Layout Structure

- Mobile (< 768px): Full width, single column
- Tablet (768px - 1024px): Full width, single column with more spacing
- Desktop (1024px - 1440px): Full width, single column
- Wide (> 1440px): Centered container with max-width 1200px

### Design Principles

- Clean article list layout
- Clear button styles
- Plain text focus (no fancy animations)
- Language buttons as small buttons
- Translation text shown below Finnish paragraphs
- Username displayed in header/navigation
- Consistent spacing and typography

### Responsive Breakpoints

    Mobile: < 768px
    Tablet: 768px - 1024px
    Desktop: 1024px - 1440px
    Wide: > 1440px (centered container, max-width 1200px)

Pseudocode:

    @media (max-width: 767px) {
        /* Mobile styles */
        container: full width, padding 16px
        font-size: 16px
        buttons: full width or stacked
    }
    
    @media (min-width: 768px) and (max-width: 1023px) {
        /* Tablet styles */
        container: full width, padding 24px
        font-size: 18px
    }
    
    @media (min-width: 1024px) and (max-width: 1439px) {
        /* Desktop styles */
        container: full width, padding 32px
        font-size: 18px
    }
    
    @media (min-width: 1440px) {
        /* Wide display styles */
        container: centered, max-width 1200px, margin auto, padding 32px
        font-size: 18px
    }

---

## Azure Static Web Apps Configuration

File: staticwebapp.config.json

    {
        "routes": [
            {
                "route": "/articles.html",
                "allowedRoles": ["authenticated"]
            },
            {
                "route": "/article.html",
                "allowedRoles": ["authenticated"]
            }
        ],
        "navigationFallback": {
            "rewrite": "/index.html"
        }
    }

Note: Authentication uses token-based system. Tokens stored in localStorage for persistence across browser sessions.

---

## Blob Storage Access

### Option 1: Public Blob Access

Configure blob container as public read access.

Pseudocode:

    function constructBlobUrl(path):
        storageAccount = "{storage-account}"
        container = CONFIG.storageContainer
        return `https://${storageAccount}.blob.core.windows.net/${container}/${path}`

### Option 2: Azure Functions Proxy

Create proxy function to serve blob content with authentication.

Pseudocode:

    function proxyBlob(path):
        url = apiBaseUrl + "/proxy-blob?path=" + path
        response = fetch(url)
        return response.json()

---

## Error Handling

- Show error message if RSS feed fails to load
- Show error message if article fails to load
- Show error message if translation fails (rate limit, API error)
- Handle 401 authentication errors: redirect to login page
- Handle 429 rate limit errors gracefully with retry message
- Show loading indicators during API calls
- Handle authentication errors (401) by redirecting to login

---

## Deployment

1. Create Azure Static Web App

    az staticwebapp create \
      --name {static-web-app-name} \
      --resource-group {resource-group} \
      --source . \
      --location {location} \
      --branch main \
      --app-location "/" \
      --output-location "dist"

2. Configure Blob Storage Access

    az storage container set-permission \
      --name {storage-container} \
      --account-name {storage-account} \
      --public-access blob

3. Deploy Files

    Copy all HTML/CSS/JS files to static web app directory
    Update config.js with correct API URLs
    Deploy via Git or Azure CLI

---

## Testing

- Test login with username and valid password
- Test login with invalid password
- Test username display in header
- Test logout functionality
- Test responsive design on mobile device
- Test responsive design on tablet
- Test responsive design on desktop
- Test centered container on wide display (> 1440px)
- Test RSS feed loading
- Test article loading
- Test translation loading
- Test language button toggles
- Test YLE link opens correctly
- Test on mobile device

---

## Security Considerations

- Tokens stored client-side only (localStorage)
- No password logic in frontend code after initial authentication
- API endpoints handle rate limiting
- Tokens can expire and require re-authentication
- Blob storage can be public read-only for cache files
- Consider adding CORS headers if needed

---

## Future Enhancements

- Remember last viewed article
- Dark mode toggle
- Article search/filter
- Bookmark articles
- Share article links
- Export translations

---

## Cost

- Azure Static Web Apps: FREE tier (<100GB bandwidth)
- Blob Storage: ~$0.018/GB/month (public read access)
- No additional frontend costs

Total frontend cost: $0-1/month
