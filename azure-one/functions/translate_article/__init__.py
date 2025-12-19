import azure.functions as func
import json
import os
import logging
from datetime import datetime, timezone
try:
    from ..shared.app import app
    from ..shared.token_validator import validate_request
    from ..shared.rate_limiter import DailyRateLimiter
    from .cache_manager import TranslationCacheManager
    from .translator import AzureTranslatorWrapper
except ImportError:
    from shared.app import app
    from shared.token_validator import validate_request
    from shared.rate_limiter import DailyRateLimiter
    from translate_article.cache_manager import TranslationCacheManager
    from translate_article.translator import AzureTranslatorWrapper

logger = logging.getLogger(__name__)


@app.route(route="translate-article", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def translate_article(req: func.HttpRequest) -> func.HttpResponse:
    logger.info('Translate Article function triggered')
    
    is_valid, username_or_error = validate_request(req)
    if not is_valid:
        logger.warning(f"Authentication failed: {username_or_error}")
        return func.HttpResponse(
            json.dumps({"error": "Authentication required"}),
            status_code=401,
            mimetype="application/json"
        )
    
    rate_limiter = DailyRateLimiter(os.getenv('RATE_LIMIT_TABLE_NAME', 'rateLimits'))
    daily_limit = int(os.getenv('TRANSLATION_DAILY_LIMIT', '50'))
    
    if not rate_limiter.check_limit('translate_article', daily_limit):
        current_count = rate_limiter.get_daily_count('translate_article')
        logger.warning(f"Rate limit exceeded for translate_article: {current_count}/{daily_limit}")
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
        body = req.get_json()
        if not body:
            return func.HttpResponse(
                json.dumps({"error": "Request body required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        article_id = body.get('article_id')
        source_lang = body.get('source_lang', 'fi')
        target_lang = body.get('target_lang', 'en')
        paragraphs = body.get('paragraphs', [])
        
        if not article_id or not paragraphs:
            return func.HttpResponse(
                json.dumps({"error": "article_id and paragraphs required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        logger.info(f"Translation requested: {article_id} {source_lang}->{target_lang}, {len(paragraphs)} paragraphs")
        
        cache_ttl_hours = int(os.getenv('TRANSLATION_CACHE_TTL_HOURS', '24'))
        cache_manager = TranslationCacheManager(cache_ttl_hours)
        
        cache_manager.cleanup_expired()
        
        cached_data = cache_manager.get(article_id, source_lang, target_lang, paragraphs)
        if cached_data:
            logger.info(f"Returning cached translation for {article_id}")
            return func.HttpResponse(
                json.dumps({
                    "article_id": article_id,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "translations": cached_data['translations'],
                    "cache_hit": True,
                    "cached_at": cached_data.get('created_at'),
                    "translated_at": cached_data.get('created_at')
                }),
                status_code=200,
                mimetype="application/json"
            )
        
        translator = AzureTranslatorWrapper(source_lang, target_lang)
        translations = translator.translate_batch(paragraphs)
        
        cache_manager.save(article_id, source_lang, target_lang, paragraphs, translations)
        rate_limiter.increment('translate_article')
        
        now = datetime.now(timezone.utc)
        return func.HttpResponse(
            json.dumps({
                "article_id": article_id,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "translations": translations,
                "cache_hit": False,
                "translated_at": now.isoformat()
            }),
            status_code=200,
            mimetype="application/json"
        )
    
    except Exception as e:
        logger.error(f"Error in translate_article function: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
