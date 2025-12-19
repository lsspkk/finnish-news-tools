import azure.functions as func
import json
import os
import logging
try:
    from ..shared.app import app
    from ..shared.token_validator import validate_request
    from ..shared.rate_limiter import DailyRateLimiter
except ImportError:
    from shared.app import app
    from shared.token_validator import validate_request
    from shared.rate_limiter import DailyRateLimiter

logger = logging.getLogger(__name__)


@app.route(route="query-rate-limits", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def query_rate_limits(req: func.HttpRequest) -> func.HttpResponse:
    logger.info('Query Rate Limits function triggered')
    
    is_valid, username_or_error = validate_request(req)
    if not is_valid:
        logger.warning(f"Authentication failed: {username_or_error}")
        return func.HttpResponse(
            json.dumps({"error": "Authentication required"}),
            status_code=401,
            mimetype="application/json"
        )
    
    function_name = req.params.get('function_name')
    
    rate_limiter = DailyRateLimiter(os.getenv('RATE_LIMIT_TABLE_NAME', 'rateLimits'))
    
    functions_config = {
        'rss_feed_parser': int(os.getenv('RSS_PARSER_DAILY_LIMIT', '50')),
        'article_scraper': int(os.getenv('ARTICLE_SCRAPER_DAILY_LIMIT', '50')),
        'translate_article': int(os.getenv('TRANSLATION_DAILY_LIMIT', '50'))
    }
    
    if function_name:
        if function_name not in functions_config:
            return func.HttpResponse(
                json.dumps({"error": f"Unknown function: {function_name}"}),
                status_code=400,
                mimetype="application/json"
            )
        
        daily_limit = functions_config[function_name]
        current_count = rate_limiter.get_daily_count(function_name)
        
        result = {
            "date": rate_limiter._get_date_key(),
            "function_name": function_name,
            "request_count": current_count,
            "daily_limit": daily_limit,
            "remaining": max(0, daily_limit - current_count),
            "percentage_used": round((current_count / daily_limit * 100), 1) if daily_limit > 0 else 0
        }
        
        return func.HttpResponse(
            json.dumps(result),
            status_code=200,
            mimetype="application/json"
        )
    else:
        results = {}
        for func_name, daily_limit in functions_config.items():
            current_count = rate_limiter.get_daily_count(func_name)
            results[func_name] = {
                "date": rate_limiter._get_date_key(),
                "request_count": current_count,
                "daily_limit": daily_limit,
                "remaining": max(0, daily_limit - current_count),
                "percentage_used": round((current_count / daily_limit * 100), 1) if daily_limit > 0 else 0
            }
        
        return func.HttpResponse(
            json.dumps(results),
            status_code=200,
            mimetype="application/json"
        )
