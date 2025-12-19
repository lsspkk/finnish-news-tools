#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

functions_dir = Path(__file__).parent.parent
sys.path.insert(0, str(functions_dir))
sys.path.insert(0, str(functions_dir.parent))

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


def test_rss_feed_parser(auth_headers: dict):
    from rss_feed_parser import main
    
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
        return json.loads(body_str)
    else:
        return {
            "error": body_str,
            "status_code": response.status_code
        }


def test_article_scraper(auth_headers: dict, article_url: str):
    from article_scraper import main
    
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
        return json.loads(body_str)
    else:
        return {
            "error": body_str,
            "status_code": response.status_code
        }


def main():
    print("=" * 60)
    print("Finnish News Scraper Test")
    print("=" * 60)
    print()
    
    username = input("Enter username: ").strip()
    if not username:
        username = "test_user"
        print(f"Using default username: {username}")
    
    password = input("Enter password: ").strip()
    if not password:
        print("Warning: No password provided. Using default.")
        password = "Hello world!"
    
    print()
    print("Authenticating...")
    auth_data = authenticate_user(username, password)
    auth_headers = create_auth_headers(auth_data)
    print(f"✓ Authenticated as: {auth_data['username']}")
    print()
    
    print("=" * 60)
    print("Step 1: Fetching RSS Feed")
    print("=" * 60)
    print()
    
    rss_result = test_rss_feed_parser(auth_headers)
    
    if "error" in rss_result:
        print(f"✗ Error fetching RSS feed: {rss_result['error']}")
        return
    else:
        print("✓ RSS Feed fetched successfully")
        print()
        print("RSS Feed Result:")
        print(json.dumps(rss_result, indent=2, ensure_ascii=False))
        print()
    
    first_article_url = None
    if "blob_path" in rss_result:
        try:
            from shared.storage_factory import get_blob_storage
            storage = get_blob_storage()
            blob_path = rss_result["blob_path"]
            feed_data = storage.read_file(blob_path) if hasattr(storage, 'read_file') else None
            
            if feed_data and "items" in feed_data and len(feed_data["items"]) > 0:
                first_article_url = feed_data["items"][0]["link"]
                print(f"Using first article from feed: {first_article_url}")
            else:
                print("Could not read feed data from storage. Using default article URL.")
                first_article_url = "https://yle.fi/a/74-20197424"
        except Exception as e:
            print(f"Error reading feed data: {e}")
            first_article_url = "https://yle.fi/a/74-20197424"
    else:
        first_article_url = "https://yle.fi/a/74-20197424"
        print(f"Using default article URL: {first_article_url}")
    
    if first_article_url:
        print("=" * 60)
        print("Step 2: Scraping First Article")
        print("=" * 60)
        print()
        
        print()
        article_result = test_article_scraper(auth_headers, first_article_url)
        
        if "error" in article_result:
            print(f"✗ Error scraping article: {article_result['error']}")
        else:
            print("✓ Article scraped successfully")
            print()
            print("Article Scraper Result:")
            print(json.dumps(article_result, indent=2, ensure_ascii=False))
            print()
            
            if "results" in article_result and len(article_result["results"]) > 0:
                result = article_result["results"][0]
                if result.get("success") and "blob_path" in result:
                    print("=" * 60)
                    print("Step 3: Reading Scraped Article Content")
                    print("=" * 60)
                    print()
                    
                    try:
                        from shared.storage_factory import get_blob_storage
                        storage = get_blob_storage()
                        article_blob_path = result["blob_path"]
                        article_data = storage.read_file(article_blob_path) if hasattr(storage, 'read_file') else None
                        
                        if article_data:
                            print("Article Content:")
                            print(json.dumps(article_data, indent=2, ensure_ascii=False))
                        else:
                            print(f"Could not read article data from {article_blob_path}")
                    except Exception as e:
                        print(f"Error reading article data: {e}")
    
    print()
    print("=" * 60)
    print("Test Complete")
    print("=" * 60)


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
