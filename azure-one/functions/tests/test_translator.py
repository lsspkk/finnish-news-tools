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


def test_translate_article(auth_headers: dict, article_id: str, paragraphs: list, source_lang: str = 'fi', target_lang: str = 'en'):
    from translate_article import main
    
    request = MockHttpRequest(
        method='POST',
        headers=auth_headers,
        body={
            "article_id": article_id,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "paragraphs": paragraphs
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


def get_scraped_article_paragraphs():
    try:
        from shared.storage_factory import get_blob_storage
        storage = get_blob_storage()
        
        article_paths = storage.list_files('cache/yle/articles/') if hasattr(storage, 'list_files') else []
        if article_paths:
            article_data = storage.read_file(article_paths[0]) if hasattr(storage, 'read_file') else None
            if article_data and 'paragraphs' in article_data:
                return article_data['paragraphs'][:3]
        
        return None
    except Exception as e:
        print(f"Could not get scraped article: {e}")
        return None


def main():
    print("=" * 60)
    print("Finnish News Translator Test")
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
    print("Step 1: Getting Article Paragraphs")
    print("=" * 60)
    print()
    
    paragraphs = get_scraped_article_paragraphs()
    if not paragraphs:
        print("No scraped article found. Using test paragraphs.")
        paragraphs = [
            "Tämä on ensimmäinen kappale suomeksi.",
            "Tämä on toinen kappale suomeksi.",
            "Tämä on kolmas kappale suomeksi."
        ]
    else:
        print(f"Using {len(paragraphs)} paragraphs from scraped article")
    
    print("Paragraphs to translate:")
    for i, para in enumerate(paragraphs, 1):
        print(f"  {i}. {para[:80]}...")
    print()
    
    article_id = "74-20197424"
    source_lang = "fi"
    target_lang = "en"
    
    print("=" * 60)
    print("Step 2: Translating Article (First Request - Cache Miss)")
    print("=" * 60)
    print()
    
    result1 = test_translate_article(auth_headers, article_id, paragraphs, source_lang, target_lang)
    
    if "error" in result1:
        print(f"✗ Error translating article: {result1['error']}")
        if result1.get('status_code') == 401:
            print("Authentication failed. Check credentials.")
        elif result1.get('status_code') == 429:
            print("Rate limit exceeded.")
        return
    else:
        print("✓ Translation completed")
        print()
        print("Translation Result:")
        print(json.dumps(result1, indent=2, ensure_ascii=False))
        print()
        
        if result1.get('cache_hit'):
            print("Note: This was a cache hit (unexpected for first request)")
        else:
            print("Note: This was a cache miss (expected for first request)")
        print()
    
    print("=" * 60)
    print("Step 3: Translating Article Again (Second Request - Cache Hit)")
    print("=" * 60)
    print()
    
    result2 = test_translate_article(auth_headers, article_id, paragraphs, source_lang, target_lang)
    
    if "error" in result2:
        print(f"✗ Error translating article: {result2['error']}")
    else:
        print("✓ Translation completed")
        print()
        print("Translation Result:")
        print(json.dumps(result2, indent=2, ensure_ascii=False))
        print()
        
        if result2.get('cache_hit'):
            print("✓ Cache hit (expected for second request)")
        else:
            print("✗ Cache miss (unexpected for second request)")
        print()
    
    print("=" * 60)
    print("Step 4: Testing Cache with Different Paragraphs")
    print("=" * 60)
    print()
    
    different_paragraphs = [
        "Tämä on erilainen kappale.",
        "Tämä on toinen erilainen kappale."
    ]
    
    result3 = test_translate_article(auth_headers, article_id, different_paragraphs, source_lang, target_lang)
    
    if "error" in result3:
        print(f"✗ Error translating article: {result3['error']}")
    else:
        print("✓ Translation completed")
        print()
        if result3.get('cache_hit'):
            print("✗ Cache hit (unexpected - paragraphs changed)")
        else:
            print("✓ Cache miss (expected - paragraphs changed)")
        print()
    
    print("=" * 60)
    print("Step 5: Checking Cache Storage")
    print("=" * 60)
    print()
    
    try:
        from shared.storage_factory import get_blob_storage
        storage = get_blob_storage()
        cache_path = 'cache/translations/'
        cache_files = storage.list_files(cache_path) if hasattr(storage, 'list_files') else []
        
        print(f"Found {len(cache_files)} cache files:")
        for cache_file in cache_files[:5]:
            print(f"  - {cache_file}")
            cache_data = storage.read_file(cache_file) if hasattr(storage, 'read_file') else None
            if cache_data:
                print(f"    Article ID: {cache_data.get('article_id')}")
                print(f"    Languages: {cache_data.get('source_lang')} -> {cache_data.get('target_lang')}")
                print(f"    Created: {cache_data.get('created_at')}")
                print(f"    Expires: {cache_data.get('expires_at')}")
    except Exception as e:
        print(f"Error checking cache: {e}")
    
    print()
    print("=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    local_settings_path = Path(__file__).parent.parent / 'local.settings.json.local'
    if local_settings_path.exists():
        with open(local_settings_path, 'r') as f:
            local_settings = json.load(f)
            values = local_settings.get('Values', {})
            for key, value in values.items():
                if key not in os.environ:
                    os.environ[key] = str(value)
    
    os.environ.setdefault('USE_LOCAL_STORAGE', 'true')
    os.environ.setdefault('LOCAL_STORAGE_PATH', './local-dev/storage')
    os.environ.setdefault('LOCAL_TABLES_PATH', './local-dev/tables')
    os.environ.setdefault('STORAGE_CONTAINER', 'finnish-news-tools')
    os.environ.setdefault('TRANSLATION_DAILY_LIMIT', '50')
    os.environ.setdefault('TRANSLATION_CACHE_TTL_HOURS', '24')
    os.environ.setdefault('RATE_LIMIT_TABLE_NAME', 'rateLimits')
    os.environ.setdefault('AUTH_SECRET', 'test-secret-key-change-in-production')
    os.environ.setdefault('AZURE_TRANSLATOR_ENDPOINT', 'https://api.cognitive.microsofttranslator.com/')
    os.environ.setdefault('AZURE_TRANSLATOR_REGION', 'westeurope')
    os.environ.setdefault('AZURE_TRANSLATOR_TIMEOUT', '30')
    os.environ.setdefault('AZURE_TRANSLATOR_MAX_RETRIES', '3')
    
    main()
