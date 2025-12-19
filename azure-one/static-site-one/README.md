# Static Site - Finnish News Reader

Local development frontend for reading Finnish news articles from cached data.

## Features

- Token-based authentication (local dev password: "Hello world!")
- View RSS feed articles list
- View article content in Finnish
- View translations if available in cache
- Responsive design (mobile, tablet, desktop, wide)

## Running Locally

Start the development server:

    python3 dev-server.py

The server will start on http://localhost:8080

Open your browser and navigate to:

    http://localhost:8080/index.html


## Data Source

The frontend reads data from `local-dev/storage/cache/` directory:
- RSS feed: `local-dev/storage/finnish-news-tools/cache/yle/paauutiset.json`
- Articles: `local-dev/storage/finnish-news-tools/cache/yle/articles/{shortcode}_{lang}.json`

**Important**: The frontend only displays data that exists in cache. It does not fetch new data.

## Pages

- `index.html` - Login page
- `articles.html` - Article list page
- `article.html` - Article detail page

## Configuration

Edit `config.js` to change:
- API endpoints
- Available languages
- Storage paths

## Development

The dev server:
- Serves static files from the current directory
- Proxies API requests to local-dev storage
- Only returns data if it exists in cache (no fetching)
- Enables CORS for local development
