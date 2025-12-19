import azure.functions as func
import json
import os
import logging
try:
    from ..shared.app import app
    from ..shared.token_validator import validate_request
    from ..shared.rate_limiter import DailyRateLimiter
    from ..shared.cache_cleaner import CacheCleaner
except ImportError:
    from shared.app import app
    from shared.token_validator import validate_request
    from shared.rate_limiter import DailyRateLimiter
    from shared.cache_cleaner import CacheCleaner

try:
    from .scraper import scrape_article
    from .config_loader import load_scraper_config
    from .storage_client import StorageClient
except ImportError:
    from article_scraper.scraper import scrape_article
    from article_scraper.config_loader import load_scraper_config
    from article_scraper.storage_client import StorageClient

logger = logging.getLogger(__name__)


@app.route(route="article-scraper", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET", "POST"])
def article_scraper(req: func.HttpRequest) -> func.HttpResponse:
    logger.info('Article Scraper function triggered')
    
    is_valid, username_or_error = validate_request(req)
    if not is_valid:
        logger.warning(f"Authentication failed: {username_or_error}")
        return func.HttpResponse(
            json.dumps({"error": "Authentication required"}),
            status_code=401,
            mimetype="application/json"
        )
    
    username = username_or_error
    
    rate_limiter = DailyRateLimiter(os.getenv('RATE_LIMIT_TABLE_NAME', 'rateLimits'))
    daily_limit = int(os.getenv('ARTICLE_SCRAPER_DAILY_LIMIT', '50'))
    
    if not rate_limiter.check_limit('article_scraper', daily_limit):
        current_count = rate_limiter.get_daily_count('article_scraper')
        logger.warning(f"Rate limit exceeded for article_scraper: {current_count}/{daily_limit}")
        return func.HttpResponse(
            json.dumps({
                "error": "Rate limit exceeded",
                "current_count": current_count,
                "daily_limit": daily_limit
            }),
            status_code=429,
            mimetype="application/json"
        )
    
    try:
        if req.method == 'POST':
            body = req.get_json()
            urls = body.get('urls', [])
            language_code = body.get('language_code', 'fi')
        else:
            url_param = req.params.get('url')
            urls = [url_param] if url_param else []
            language_code = req.params.get('language_code', 'fi')
        
        if not urls:
            return func.HttpResponse(
                json.dumps({"error": "No URLs provided"}),
                status_code=400,
                mimetype="application/json"
            )
        
        config = load_scraper_config()
        storage_client = StorageClient()
        cache_ttl_hours = int(os.getenv('CACHE_TTL_HOURS', '1'))
        cache_cleaner = CacheCleaner()
        
        cache_cleaner.cleanup_expired('cache/yle/articles/', cache_ttl_hours)
        
        results = []
        for url in urls:
            try:
                try:
                    from .scraper import extract_shortcode
                except ImportError:
                    from article_scraper.scraper import extract_shortcode
                shortcode = extract_shortcode(url)
                blob_path = f"cache/yle/articles/{shortcode}_{language_code}.json"
                
                if cache_cleaner.check_cache_valid(blob_path, cache_ttl_hours):
                    logger.info(f"Returning cached article: {blob_path}")
                    cached_data = storage_client.get_article(blob_path)
                    if cached_data:
                        results.append({
                            "success": True,
                            "cached": True,
                            "url": cached_data.get('url', url),
                            "shortcode": cached_data.get('shortcode', shortcode),
                            "title": cached_data.get('title', ''),
                            "paragraphs": cached_data.get('paragraphs', []),
                            "paragraphs_count": len(cached_data.get('paragraphs', [])),
                            "blob_path": blob_path,
                            "scraped_at": cached_data.get('scraped_at'),
                            "scraper_version": cached_data.get('scraper_version')
                        })
                        continue
                
                article_data = scrape_article(url, config, language_code, cache_ttl_hours)
                storage_client.save_article(article_data, blob_path)
                
                results.append({
                    "success": True,
                    "cached": False,
                    "url": article_data.get('url', url),
                    "shortcode": article_data.get('shortcode'),
                    "title": article_data.get('title', ''),
                    "paragraphs": article_data.get('paragraphs', []),
                    "paragraphs_count": len(article_data.get('paragraphs', [])),
                    "blob_path": blob_path,
                    "scraped_at": article_data.get('scraped_at'),
                    "scraper_version": article_data.get('scraper_version')
                })
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}", exc_info=True)
                results.append({
                    "success": False,
                    "url": url,
                    "error": str(e)
                })
        
        rate_limiter.increment('article_scraper')
        
        return func.HttpResponse(
            json.dumps({
                "success": True,
                "results": results,
                "total": len(results),
                "succeeded": len([r for r in results if r.get('success')])
            }),
            status_code=200,
            mimetype="application/json"
        )
    
    except Exception as e:
        logger.error(f"Error in article scraper: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
