#!/usr/bin/env python3
"""
Test file for translation cache functionality.

Tests that translations are properly cached and retrieved from JSON cache files.
"""
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, call

# Add parent directory to path to import translator modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from translate_news import (
    get_cache_dir,
    get_cache_file_path,
    load_cache_file,
    save_cache_file,
    load_from_cache,
    save_to_cache,
    translate_with_cache,
    get_text_hash
)
from translators.libretranslate import LibreTranslateTranslator


def test_cache_file_operations():
    """Test basic JSON cache file operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / 'libretranslate'
        cache_dir.mkdir(parents=True)
        
        source_lang = "fi"
        target_lang = "es"
        text_hash = get_text_hash("Hei maailma")
        
        # Test saving to cache
        translation = "Hola mundo"
        save_to_cache(cache_dir, text_hash, source_lang, target_lang, translation)
        
        # Verify JSON file was created
        cache_file = get_cache_file_path(cache_dir, source_lang, target_lang)
        assert cache_file.exists(), "Cache file should exist after saving"
        
        # Verify JSON structure
        cache_data = load_cache_file(cache_file)
        assert text_hash in cache_data, "Text hash should be in cache"
        assert cache_data[text_hash] == translation, f"Expected '{translation}', got '{cache_data[text_hash]}'"
        
        # Test loading from cache
        cached = load_from_cache(cache_dir, text_hash, source_lang, target_lang)
        assert cached == translation, f"Expected '{translation}', got '{cached}'"
        
        # Test loading non-existent cache
        non_existent = load_from_cache(cache_dir, "nonexistent_hash", source_lang, target_lang)
        assert non_existent is None, "Non-existent cache should return None"
        
        print("✓ Cache file operations test passed")


def test_translate_with_cache():
    """Test translation with cache - verify API is only called once."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / 'libretranslate'
        cache_dir.mkdir(parents=True)
        
        # Create a mock translator
        mock_translator = Mock(spec=LibreTranslateTranslator)
        mock_translator.translate.return_value = "Hola mundo"
        
        text = "Hei maailma"
        source_lang = "fi"
        target_lang = "es"
        
        # First call - should call API and save to cache
        result1 = translate_with_cache(mock_translator, text, source_lang, target_lang, cache_dir)
        assert result1 == "Hola mundo", "First translation should return API result"
        assert mock_translator.translate.call_count == 1, "API should be called once on first request"
        
        # Verify cache file was created
        cache_file = get_cache_file_path(cache_dir, source_lang, target_lang)
        assert cache_file.exists(), "Cache file should exist after first translation"
        
        # Verify JSON contains the translation
        cache_data = load_cache_file(cache_file)
        text_hash = get_text_hash(text)
        assert text_hash in cache_data, "Text hash should be in cache"
        assert cache_data[text_hash] == "Hola mundo", "Cache should contain translation"
        
        # Reset mock to track second call
        mock_translator.reset_mock()
        
        # Second call - should load from cache, not call API
        result2 = translate_with_cache(mock_translator, text, source_lang, target_lang, cache_dir)
        assert result2 == "Hola mundo", "Second translation should return cached result"
        assert mock_translator.translate.call_count == 0, "API should not be called on second request (should use cache)"
        
        print("✓ Translation with cache test passed")


def test_cache_directory_structure():
    """Test that cache directories are created correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        
        # Test get_cache_dir creates directory
        cache_dir = get_cache_dir("libretranslate", str(base_dir / "cache"))
        assert cache_dir.exists(), "Cache directory should be created"
        assert cache_dir.name == "libretranslate", "Cache directory should be named after service"
        
        # Test with different service name
        cache_dir2 = get_cache_dir("deepl", str(base_dir / "cache"))
        assert cache_dir2.exists(), "Second cache directory should be created"
        assert cache_dir2.name == "deepl", "Second cache directory should have correct name"
        assert cache_dir != cache_dir2, "Different services should have different cache directories"
        
        print("✓ Cache directory structure test passed")


def test_hei_maailma_to_spanish():
    """Integration test: Translate 'Hei maailma' to Spanish and verify JSON cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / 'libretranslate'
        cache_dir.mkdir(parents=True)
        
        # Initialize translator (using real API, but with cache)
        translator = LibreTranslateTranslator(
            source_lang='fi',
            target_langs=['es'],
            api_url='https://libretranslate.com/translate',
            timeout=30
        )
        
        text = "Hei maailma"
        source_lang = "fi"
        target_lang = "es"
        
        # First translation - should call API
        print(f"Translating '{text}' to {target_lang} (first call, will use API)...")
        result1 = translate_with_cache(translator, text, source_lang, target_lang, cache_dir)
        print(f"Result: {result1}")
        
        # Verify JSON cache file exists
        cache_file = get_cache_file_path(cache_dir, source_lang, target_lang)
        assert cache_file.exists(), "Cache file should exist after translation"
        
        # Read and verify JSON cache file
        cache_data = load_cache_file(cache_file)
        text_hash = get_text_hash(text)
        assert text_hash in cache_data, "Text hash should be in cache"
        assert cache_data[text_hash] == result1, "Cache file should contain the translation"
        
        # Verify JSON structure is valid
        with open(cache_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        assert isinstance(json_data, dict), "Cache file should contain a JSON object"
        assert text_hash in json_data, "Cache should contain the text hash"
        
        # Second translation - should use cache
        print(f"Translating '{text}' to {target_lang} again (should use cache)...")
        
        # Mock the translator to verify it's not called
        with patch.object(translator, 'translate') as mock_translate:
            result2 = translate_with_cache(translator, text, source_lang, target_lang, cache_dir)
            assert mock_translate.call_count == 0, "Translator should not be called when using cache"
            assert result2 == result1, "Cached result should match first result"
        
        print(f"Cached result: {result2}")
        print("✓ 'Hei maailma' to Spanish cache test passed")


if __name__ == '__main__':
    print("Running cache tests...\n")
    
    try:
        test_cache_file_operations()
        print()
        
        test_translate_with_cache()
        print()
        
        test_cache_directory_structure()
        print()
        
        # This test requires internet connection and API access
        print("Running integration test (requires internet connection)...")
        test_hei_maailma_to_spanish()
        print()
        
        print("\n✓ All cache tests passed!")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
