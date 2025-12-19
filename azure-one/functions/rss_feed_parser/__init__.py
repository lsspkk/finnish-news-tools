import azure.functions as func
import json
import os
import logging
try:
    from ..shared.app import app
    from ..shared.token_validator import validate_request
    from ..shared.rate_limiter import DailyRateLimiter
    from ..shared.cache_cleaner import CacheCleaner
    from ..shared.cors_helper import add_cors_headers, create_cors_response
except ImportError:
    from shared.app import app
    from shared.token_validator import validate_request
    from shared.rate_limiter import DailyRateLimiter
    from shared.cache_cleaner import CacheCleaner
    from shared.cors_helper import add_cors_headers, create_cors_response

try:
    from .rss_parser import parse_rss_feed
    from .storage_client import StorageClient
except ImportError:
    from rss_feed_parser.rss_parser import parse_rss_feed
    from rss_feed_parser.storage_client import StorageClient

logger = logging.getLogger(__name__)


@app.route(route="rss-feed-parser", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET", "POST"])
def rss_feed_parser(req: func.HttpRequest) -> func.HttpResponse:
    logger.info('RSS Feed Parser function triggered')
    
    is_valid, username_or_error = validate_request(req)
    if not is_valid:
        logger.warning(f"Authentication failed: {username_or_error}")
        return create_cors_response(
            json.dumps({"error": "Authentication required"}),
            status_code=401,
            mimetype="application/json",
            request=req
        )
    
    username = username_or_error
    
    rate_limiter = DailyRateLimiter(os.getenv('RATE_LIMIT_TABLE_NAME', 'rateLimits'))
    daily_limit = int(os.getenv('RSS_PARSER_DAILY_LIMIT', '50'))
    
    if not rate_limiter.check_limit('rss_feed_parser', daily_limit):
        current_count = rate_limiter.get_daily_count('rss_feed_parser')
        logger.warning(f"Rate limit exceeded for rss_feed_parser: {current_count}/{daily_limit}")
        return create_cors_response(
            json.dumps({
                "error": "Rate limit exceeded",
                "current_count": current_count,
                "daily_limit": daily_limit
            }),
            status_code=429,
            mimetype="application/json",
            request=req
        )
    
    feed_url = req.params.get('url') or os.getenv('RSS_FEED_URL', 'https://yle.fi/rss/uutiset/paauutiset')
    add_origin_rss = os.getenv('ADD_ORIGIN_RSS', 'true').lower() == 'true'
    cache_ttl_hours = int(os.getenv('CACHE_TTL_HOURS', '1'))
    force_reload = req.params.get('force_reload', 'false').lower() == 'true'
    
    storage_client = StorageClient()
    blob_path = 'cache/yle/paauutiset.json'
    cache_cleaner = CacheCleaner()
    
    cache_cleaner.cleanup_expired('cache/yle/', cache_ttl_hours)
    
    if not force_reload and cache_cleaner.check_cache_valid(blob_path, cache_ttl_hours):
        logger.info("Returning cached RSS feed")
        cached_data = storage_client.get_rss_feed(blob_path)
        if cached_data:
            response = func.HttpResponse(
                json.dumps(cached_data),
                status_code=200,
                mimetype="application/json"
            )
            return add_cors_headers(response, req)
    
    try:
        feed_data = parse_rss_feed(feed_url, add_origin_rss, cache_ttl_hours)
        
        storage_client.save_rss_feed(feed_data, blob_path)
        
        rate_limiter.increment('rss_feed_parser')
        
        logger.info(f"Fetched and saved RSS feed with {len(feed_data['items'])} items")
        
        response = func.HttpResponse(
            json.dumps(feed_data),
            status_code=200,
            mimetype="application/json"
        )
        return add_cors_headers(response, req)
    
    except Exception as e:
        logger.error(f"Error parsing RSS feed: {e}", exc_info=True)
        return create_cors_response(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
            request=req
        )
