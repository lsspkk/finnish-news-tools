#!/usr/bin/env python3
import os
import sys
import json
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path

functions_dir = Path(__file__).parent.parent / 'functions'
sys.path.insert(0, str(functions_dir.parent))
sys.path.insert(0, str(functions_dir))

from functions.shared.cache_cleaner import CacheCleaner
from functions.shared.local_storage import LocalBlobStorage


@pytest.fixture
def temp_storage(tmp_path):
    storage_path = tmp_path / "storage"
    return LocalBlobStorage(str(storage_path))


@pytest.fixture
def cache_cleaner(temp_storage, monkeypatch):
    monkeypatch.setenv('USE_LOCAL_STORAGE', 'true')
    monkeypatch.setenv('STORAGE_CONTAINER', 'test-container')
    
    from functions.shared.storage_factory import get_blob_storage
    original_get = get_blob_storage
    
    def mock_get_blob_storage():
        return temp_storage
    
    monkeypatch.setattr('functions.shared.cache_cleaner.get_blob_storage', mock_get_blob_storage)
    
    return CacheCleaner()


def test_cache_cleaner_check_valid_cache(cache_cleaner, temp_storage):
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=1)
    
    cache_data = {
        'feed_metadata': {'title': 'Test Feed'},
        'items': [],
        'expires_at': expires_at.isoformat(),
        'cache_ttl_hours': 1
    }
    
    temp_storage.save_file('cache/yle/paauutiset.json', cache_data)
    
    assert cache_cleaner.check_cache_valid('cache/yle/paauutiset.json', ttl_hours=1) == True


def test_cache_cleaner_check_expired_cache(cache_cleaner, temp_storage):
    now = datetime.now(timezone.utc)
    expires_at = now - timedelta(hours=1)
    
    cache_data = {
        'feed_metadata': {'title': 'Test Feed'},
        'items': [],
        'expires_at': expires_at.isoformat(),
        'cache_ttl_hours': 1
    }
    
    temp_storage.save_file('cache/yle/paauutiset.json', cache_data)
    
    assert cache_cleaner.check_cache_valid('cache/yle/paauutiset.json', ttl_hours=1) == False


def test_cache_cleaner_check_cache_with_timestamp(cache_cleaner, temp_storage):
    now = datetime.now(timezone.utc)
    fetch_time = now - timedelta(minutes=30)
    
    cache_data = {
        'feed_metadata': {
            'title': 'Test Feed',
            'fetch_timestamp': fetch_time.isoformat()
        },
        'items': []
    }
    
    temp_storage.save_file('cache/yle/paauutiset.json', cache_data)
    
    assert cache_cleaner.check_cache_valid('cache/yle/paauutiset.json', ttl_hours=1) == True


def test_cache_cleaner_check_expired_cache_with_timestamp(cache_cleaner, temp_storage):
    now = datetime.now(timezone.utc)
    fetch_time = now - timedelta(hours=2)
    
    cache_data = {
        'feed_metadata': {
            'title': 'Test Feed',
            'fetch_timestamp': fetch_time.isoformat()
        },
        'items': []
    }
    
    temp_storage.save_file('cache/yle/paauutiset.json', cache_data)
    
    assert cache_cleaner.check_cache_valid('cache/yle/paauutiset.json', ttl_hours=1) == False


def test_cache_cleaner_cleanup_expired(cache_cleaner, temp_storage):
    now = datetime.now(timezone.utc)
    
    expired_data = {
        'feed_metadata': {'title': 'Expired Feed'},
        'items': [],
        'expires_at': (now - timedelta(hours=1)).isoformat(),
        'cache_ttl_hours': 1
    }
    
    valid_data = {
        'feed_metadata': {'title': 'Valid Feed'},
        'items': [],
        'expires_at': (now + timedelta(hours=1)).isoformat(),
        'cache_ttl_hours': 1
    }
    
    temp_storage.save_file('cache/yle/expired.json', expired_data)
    temp_storage.save_file('cache/yle/valid.json', valid_data)
    
    cleaned = cache_cleaner.cleanup_expired('cache/yle/', ttl_hours=1)
    
    assert cleaned == 1
    assert not temp_storage.file_exists('cache/yle/expired.json')
    assert temp_storage.file_exists('cache/yle/valid.json')


def test_cache_cleaner_cleanup_expired_with_timestamp(cache_cleaner, temp_storage):
    now = datetime.now(timezone.utc)
    
    expired_data = {
        'feed_metadata': {
            'title': 'Expired Feed',
            'fetch_timestamp': (now - timedelta(hours=2)).isoformat()
        },
        'items': []
    }
    
    valid_data = {
        'feed_metadata': {
            'title': 'Valid Feed',
            'fetch_timestamp': (now - timedelta(minutes=30)).isoformat()
        },
        'items': []
    }
    
    temp_storage.save_file('cache/yle/expired.json', expired_data)
    temp_storage.save_file('cache/yle/valid.json', valid_data)
    
    cleaned = cache_cleaner.cleanup_expired('cache/yle/', ttl_hours=1)
    
    assert cleaned == 1
    assert not temp_storage.file_exists('cache/yle/expired.json')
    assert temp_storage.file_exists('cache/yle/valid.json')


def test_article_cache_with_expires_at(cache_cleaner, temp_storage):
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=1)
    
    article_data = {
        'url': 'https://yle.fi/a/74-20197424',
        'shortcode': '74-20197424',
        'title': 'Test Article',
        'paragraphs': ['Paragraph 1', 'Paragraph 2'],
        'scraped_at': now.isoformat(),
        'expires_at': expires_at.isoformat(),
        'cache_ttl_hours': 1
    }
    
    temp_storage.save_file('cache/yle/articles/74-20197424_fi.json', article_data)
    
    assert cache_cleaner.check_cache_valid('cache/yle/articles/74-20197424_fi.json', ttl_hours=1) == True


def test_article_cache_expired(cache_cleaner, temp_storage):
    now = datetime.now(timezone.utc)
    expires_at = now - timedelta(hours=1)
    
    article_data = {
        'url': 'https://yle.fi/a/74-20197424',
        'shortcode': '74-20197424',
        'title': 'Test Article',
        'paragraphs': ['Paragraph 1'],
        'scraped_at': (now - timedelta(hours=2)).isoformat(),
        'expires_at': expires_at.isoformat(),
        'cache_ttl_hours': 1
    }
    
    temp_storage.save_file('cache/yle/articles/74-20197424_fi.json', article_data)
    
    assert cache_cleaner.check_cache_valid('cache/yle/articles/74-20197424_fi.json', ttl_hours=1) == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
