#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

functions_dir = Path(__file__).parent.parent
sys.path.insert(0, str(functions_dir))
sys.path.insert(0, str(functions_dir.parent))

os.environ.setdefault('USE_LOCAL_STORAGE', 'true')
os.environ.setdefault('LOCAL_STORAGE_PATH', './local-dev/storage')
os.environ.setdefault('STORAGE_CONTAINER', 'finnish-news-tools')

from translate_article.cache_manager import TranslationCacheManager, hash_paragraphs


def test_hash_paragraphs():
    print("Testing hash_paragraphs...")
    para1 = ["Test paragraph 1", "Test paragraph 2"]
    para2 = ["Test paragraph 1", "Test paragraph 2"]
    para3 = ["Different paragraph"]
    
    hash1 = hash_paragraphs(para1)
    hash2 = hash_paragraphs(para2)
    hash3 = hash_paragraphs(para3)
    
    assert hash1 == hash2, "Same paragraphs should produce same hash"
    assert hash1 != hash3, "Different paragraphs should produce different hash"
    print("✓ hash_paragraphs works correctly")
    print()


def test_cache_save_and_get():
    print("Testing cache save and get...")
    
    cache_manager = TranslationCacheManager(cache_ttl_hours=24)
    
    article_id = "test-article-123"
    source_lang = "fi"
    target_lang = "en"
    paragraphs = ["Tämä on testi.", "Tämä on toinen testi."]
    translations = ["This is a test.", "This is another test."]
    
    cache_manager.save(article_id, source_lang, target_lang, paragraphs, translations)
    print(f"✓ Saved cache for {article_id}")
    
    cached_data = cache_manager.get(article_id, source_lang, target_lang, paragraphs)
    assert cached_data is not None, "Should retrieve cached data"
    assert cached_data['translations'] == translations, "Translations should match"
    assert cached_data['article_id'] == article_id, "Article ID should match"
    print(f"✓ Retrieved cache for {article_id}")
    print()


def test_cache_miss_different_paragraphs():
    print("Testing cache miss with different paragraphs...")
    
    cache_manager = TranslationCacheManager(cache_ttl_hours=24)
    
    article_id = "test-article-456"
    source_lang = "fi"
    target_lang = "en"
    paragraphs1 = ["Ensimmäinen kappale."]
    paragraphs2 = ["Toinen kappale."]
    translations = ["First paragraph."]
    
    cache_manager.save(article_id, source_lang, target_lang, paragraphs1, translations)
    
    cached_data = cache_manager.get(article_id, source_lang, target_lang, paragraphs2)
    assert cached_data is None, "Should return None for different paragraphs"
    print("✓ Cache correctly rejects different paragraphs")
    print()


def test_cache_hit_on_repeated_request():
    print("Testing cache hit on repeated request...")
    
    cache_manager = TranslationCacheManager(cache_ttl_hours=24)
    
    article_id = "test-article-repeat"
    source_lang = "fi"
    target_lang = "en"
    paragraphs = ["Ensimmäinen kappale.", "Toinen kappale."]
    translations = ["First paragraph.", "Second paragraph."]
    
    first_get = cache_manager.get(article_id, source_lang, target_lang, paragraphs)
    assert first_get is None, "First request should have no cache"
    print("✓ First request: cache miss (no cache found)")
    
    cache_manager.save(article_id, source_lang, target_lang, paragraphs, translations)
    print("✓ Saved cache")
    
    second_get = cache_manager.get(article_id, source_lang, target_lang, paragraphs)
    assert second_get is not None, "Second request should have cache"
    assert second_get['translations'] == translations, "Cached translations should match"
    print("✓ Second request: cache hit (cache found)")
    print()


def main():
    print("=" * 60)
    print("Translation Cache Manager Tests")
    print("=" * 60)
    print()
    
    try:
        test_hash_paragraphs()
        test_cache_save_and_get()
        test_cache_miss_different_paragraphs()
        test_cache_hit_on_repeated_request()
        
        print("=" * 60)
        print("All Tests Passed!")
        print("=" * 60)
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
