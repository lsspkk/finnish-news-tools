#!/usr/bin/env python3
import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

functions_dir = Path(__file__).parent.parent
sys.path.insert(0, str(functions_dir.parent))
sys.path.insert(0, str(functions_dir))

from shared.token_validator import generate_token
import azure.functions as func


class MockHeaders:
    def __init__(self, headers_dict):
        self._headers = headers_dict
    
    def get(self, key, default=None):
        return self._headers.get(key, default)


class MockParams:
    def __init__(self, params_dict):
        self._params = params_dict
    
    def get(self, key, default=None):
        return self._params.get(key, default)


class MockHttpRequest:
    def __init__(self, method='GET', params=None, body=None, headers=None):
        self.method = method
        self.params = MockParams(params or {})
        self._body = body
        self.headers = MockHeaders(headers or {})
    
    def get(self, key, default=None):
        return self.params.get(key, default)
    
    def get_json(self):
        if isinstance(self._body, dict):
            return self._body
        if isinstance(self._body, str):
            return json.loads(self._body)
        return self._body
    
    def get_header(self, name):
        return self.headers.get(name)


def authenticate_user(username: str, password: str) -> dict:
    from authenticate import main as authenticate_main
    
    request = MockHttpRequest(
        method='POST',
        body={
            "username": username,
            "password": password
        }
    )
    
    response = authenticate_main(request)
    
    body_bytes = response.get_body()
    if isinstance(body_bytes, bytes):
        body_str = body_bytes.decode('utf-8')
    else:
        body_str = str(body_bytes)
    
    if response.status_code == 200:
        auth_data = json.loads(body_str)
        return {
            "token": auth_data["token"],
            "username": auth_data["username"],
            "issued_date": auth_data["issued_at"]
        }
    else:
        error_data = json.loads(body_str)
        raise ValueError(f"Authentication failed: {error_data.get('error', 'Unknown error')}")


def create_auth_headers(auth_data: dict) -> dict:
    return {
        "X-Token": auth_data["token"],
        "X-Username": auth_data["username"],
        "X-Issued-Date": auth_data["issued_date"]
    }


def check_cache_status():
    from rss_feed_parser.storage_client import StorageClient as RSSStorageClient
    from article_scraper.storage_client import StorageClient as ArticleStorageClient
    
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("Checking Cache/Storage Status")
    logger.info("=" * 60)
    
    rss_storage = RSSStorageClient()
    article_storage = ArticleStorageClient()
    
    rss_status = rss_storage.get_cache_status()
    article_status = article_storage.get_cache_status()
    
    logger.info("\nRSS Feed Cache Status:")
    logger.info(f"  Path: {rss_status['rss_feed_path']}")
    logger.info(f"  Exists: {rss_status['rss_feed_exists']}")
    logger.info(f"  Items Count: {rss_status['rss_feed_items_count']}")
    logger.info(f"  Title: {rss_status['rss_feed_title']}")
    logger.info(f"  Last Fetch: {rss_status['rss_feed_last_fetch']}")
    
    logger.info("\nArticle Cache Status:")
    logger.info(f"  Prefix: {article_status['articles_prefix']}")
    logger.info(f"  Articles Count: {article_status['articles_count']}")
    if article_status['article_paths']:
        logger.info(f"  Sample Articles:")
        for path in article_status['article_paths'][:5]:
            logger.info(f"    - {path}")
    
    logger.info("=" * 60)
    logger.info("")
    
    return rss_status, article_status


def fetch_rss_feed_if_needed(auth_headers: dict, rss_status: dict):
    from rss_feed_parser import main
    
    logger = logging.getLogger(__name__)
    
    if rss_status['rss_feed_exists']:
        logger.info(f"RSS feed already cached ({rss_status['rss_feed_items_count']} items)")
        logger.info(f"  Path: {rss_status['rss_feed_path']}")
        logger.info(f"  Title: {rss_status['rss_feed_title']}")
        return None
    
    logger.info("RSS feed not found in cache, fetching...")
    
    request = MockHttpRequest(
        method='GET',
        headers=auth_headers
    )
    
    response = main(request)
    
    body_bytes = response.get_body()
    if isinstance(body_bytes, bytes):
        body_str = body_bytes.decode('utf-8')
    else:
        body_str = str(body_bytes)
    
    if response.status_code == 200:
        result = json.loads(body_str)
        logger.info(f"✓ RSS feed fetched successfully ({result.get('items_count', 0)} items)")
        return result
    else:
        logger.error(f"✗ Error fetching RSS feed: {body_str}")
        return None


def fetch_article_if_needed(auth_headers: dict, rss_status: dict, article_status: dict):
    from rss_feed_parser.storage_client import StorageClient as RSSStorageClient
    from article_scraper import main
    
    logger = logging.getLogger(__name__)
    
    if not rss_status['rss_feed_exists']:
        logger.warning("Cannot fetch article: RSS feed not available")
        return None
    
    rss_storage = RSSStorageClient()
    feed_data = rss_storage.get_rss_feed(rss_status['rss_feed_path'])
    
    if not feed_data or not feed_data.get('items'):
        logger.warning("Cannot fetch article: RSS feed has no items")
        return None
    
    first_item = feed_data['items'][0]
    article_url = first_item.get('link', '')
    shortcode = first_item.get('shortcode', '')
    
    if not article_url:
        logger.warning("Cannot fetch article: No URL in RSS feed item")
        return None
    
    article_blob_path = f"cache/yle/articles/{shortcode}_fi.json"
    from article_scraper.storage_client import StorageClient as ArticleStorageClient
    article_storage = ArticleStorageClient()
    
    if article_storage.check_article_exists(article_blob_path):
        logger.info(f"Article already cached: {shortcode}")
        logger.info(f"  Path: {article_blob_path}")
        article_data = article_storage.get_article(article_blob_path)
        if article_data:
            logger.info(f"  Title: {article_data.get('title', 'N/A')}")
            logger.info(f"  Paragraphs: {len(article_data.get('paragraphs', []))}")
        return article_data
    
    logger.info(f"Article not found in cache, scraping: {article_url}")
    
    request = MockHttpRequest(
        method='POST',
        headers=auth_headers,
        body={
            "urls": [article_url],
            "language_code": "fi"
        }
    )
    
    response = main(request)
    
    body_bytes = response.get_body()
    if isinstance(body_bytes, bytes):
        body_str = body_bytes.decode('utf-8')
    else:
        body_str = str(body_bytes)
    
    if response.status_code == 200:
        result = json.loads(body_str)
        if result.get('success') and result.get('results'):
            article_result = result['results'][0]
            if article_result.get('success'):
                logger.info(f"✓ Article scraped successfully: {article_result.get('shortcode')}")
                logger.info(f"  Path: {article_result.get('blob_path')}")
                logger.info(f"  Paragraphs: {article_result.get('paragraphs_count', 0)}")
                return article_result
        logger.error(f"✗ Error scraping article: {result}")
        return None
    else:
        logger.error(f"✗ Error scraping article: {body_str}")
        return None


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("Cache-Aware Scraper Test")
    logger.info("=" * 60)
    logger.info("")
    
    username = input("Enter username: ").strip()
    if not username:
        username = "test_user"
        logger.info(f"Using default username: {username}")
    
    password = input("Enter password: ").strip()
    if not password:
        logger.info("Warning: No password provided. Using default.")
        password = "Hello world!"
    
    logger.info("")
    logger.info("Authenticating...")
    auth_data = authenticate_user(username, password)
    auth_headers = create_auth_headers(auth_data)
    logger.info(f"✓ Authenticated as: {auth_data['username']}")
    logger.info("")
    
    rss_status, article_status = check_cache_status()
    
    logger.info("=" * 60)
    logger.info("Step 1: Fetching RSS Feed (if needed)")
    logger.info("=" * 60)
    logger.info("")
    
    rss_result = fetch_rss_feed_if_needed(auth_headers, rss_status)
    
    if rss_result:
        logger.info("")
        logger.info("RSS Feed Result:")
        print(json.dumps(rss_result, indent=2, ensure_ascii=False))
        logger.info("")
    
    logger.info("=" * 60)
    logger.info("Step 2: Fetching Article (if needed)")
    logger.info("=" * 60)
    logger.info("")
    
    rss_status, article_status = check_cache_status()
    article_result = fetch_article_if_needed(auth_headers, rss_status, article_status)
    
    if article_result:
        logger.info("")
        logger.info("Article Result:")
        if isinstance(article_result, dict) and 'blob_path' in article_result:
            from article_scraper.storage_client import StorageClient as ArticleStorageClient
            article_storage = ArticleStorageClient()
            article_data = article_storage.get_article(article_result['blob_path'])
            if article_data:
                print(json.dumps(article_data, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(article_result, indent=2, ensure_ascii=False))
        logger.info("")
    
    logger.info("=" * 60)
    logger.info("Final Cache Status")
    logger.info("=" * 60)
    logger.info("")
    
    final_rss_status, final_article_status = check_cache_status()
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test Complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    os.environ.setdefault('USE_LOCAL_STORAGE', 'true')
    os.environ.setdefault('LOCAL_STORAGE_PATH', './local-dev/storage')
    os.environ.setdefault('LOCAL_TABLES_PATH', './local-dev/tables')
    os.environ.setdefault('STORAGE_CONTAINER', 'finnish-news-tools')
    os.environ.setdefault('RSS_FEED_URL', 'https://yle.fi/rss/uutiset/paauutiset')
    os.environ.setdefault('ADD_ORIGIN_RSS', 'true')
    os.environ.setdefault('RSS_PARSER_DAILY_LIMIT', '50')
    os.environ.setdefault('ARTICLE_SCRAPER_DAILY_LIMIT', '50')
    os.environ.setdefault('RATE_LIMIT_TABLE_NAME', 'rateLimits')
    os.environ.setdefault('CACHE_TTL_HOURS', '1')
    os.environ.setdefault('AUTH_SECRET', 'test-secret-key-change-in-production')
    config_path = str(Path(__file__).parent.parent / 'scraper-config.yaml.local')
    if os.path.exists(config_path):
        os.environ.setdefault('SCRAPER_CONFIG_PATH', config_path)
    else:
        os.environ.setdefault('SCRAPER_CONFIG_PATH', str(Path(__file__).parent.parent / 'scraper-config.yaml.template'))
    
    main()

