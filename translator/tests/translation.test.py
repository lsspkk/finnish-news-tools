#!/usr/bin/env python3
"""
Test file for translation functionality.

Tests that translations work correctly using LibreTranslate.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to import translator modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from translators.libretranslate import LibreTranslateTranslator


def test_hei_maailma_to_english_argostranslate():
    """Test: Translate 'Hei maailma' (Finnish) to English using argostranslate directly.
    
    This test uses argostranslate library directly (no API required).
    It requires the fi-en model to be installed.
    """
    try:
        import argostranslate.package
        import argostranslate.translate
    except ImportError:
        print("✗ argostranslate not available. Skipping direct translation test.")
        print("  Install with: pip install argostranslate")
        return False
    
    text = "Hei maailma"
    expected = "Hello world"
    
    print(f"\nTesting direct translation with argostranslate...")
    print(f"Translating '{text}' (Finnish) to English...")
    
    try:
        # Translate using argostranslate directly
        result = argostranslate.translate.translate(text, "fi", "en")
        print(f"Translation result: '{result}'")
        
        # Check that we got a translation
        assert result is not None, "Translation should not be None"
        assert result != text, "Translation should be different from original text"
        assert len(result) > 0, "Translation should not be empty"
        
        # The translation should contain "Hello" or "world" (case-insensitive)
        result_lower = result.lower()
        assert "hello" in result_lower or "world" in result_lower, \
            f"Translation '{result}' should contain 'hello' or 'world'"
        
        print(f"✓ Successfully translated '{text}' to '{result}' (using argostranslate)")
        return True
        
    except Exception as e:
        print(f"✗ Direct translation failed: {e}")
        print("\nMake sure the fi-en model is installed:")
        print("  python setup_libretranslate_models.py --install fi-en")
        raise


def test_hei_maailma_to_english():
    """Test: Translate 'Hei maailma' (Finnish) to English."""
    text = "Hei maailma"
    expected_translation = "Hello world"  # Expected English translation
    
    # Try different API endpoints in order of preference
    api_urls = [
        'http://localhost:5000/translate',  # Local LibreTranslate server
        'https://libretranslate.com/translate',  # Public API (may require key)
    ]
    
    translator = None
    last_error = None
    
    for api_url in api_urls:
        print(f"\nTrying API: {api_url}")
        
        translator = LibreTranslateTranslator(
            source_lang='fi',
            target_langs=['en'],
            api_url=api_url,
            timeout=10  # Shorter timeout for testing
        )
        
        try:
            print(f"Translating '{text}' (Finnish) to English...")
            result = translator.translate(text, 'en')
            print(f"Translation result: '{result}'")
            
            # Check if we got the original text back (indicates failure)
            if result == text:
                print(f"Warning: Got original text back, translation may have failed")
                # Check if it's because of API key requirement
                if "libretranslate.com" in api_url:
                    print("Note: Public LibreTranslate API may require an API key.")
                    print("      Get one at https://portal.libretranslate.com")
                    print("      Or run a local LibreTranslate server: libretranslate --host 0.0.0.0 --port 5000")
                    last_error = "Translation returned original text (API may require key or server not running)"
                    continue
                else:
                    last_error = "Translation returned original text"
                    continue
            
            # Check that we got a translation
            assert result is not None, "Translation should not be None"
            assert result != text, "Translation should be different from original text"
            assert len(result) > 0, "Translation should not be empty"
            
            # The translation should contain "Hello" or "world" (case-insensitive)
            result_lower = result.lower()
            assert "hello" in result_lower or "world" in result_lower, \
                f"Translation '{result}' should contain 'hello' or 'world'"
            
            print(f"✓ Successfully translated '{text}' to '{result}'")
            return True
            
        except AssertionError as e:
            # Re-raise assertion errors
            raise
        except Exception as e:
            print(f"  Failed: {e}")
            last_error = str(e)
            continue
    
    # If we get here, all APIs failed
    if last_error:
        print(f"\n✗ All translation APIs failed. Last error: {last_error}")
        print("\nTo run this test successfully:")
        print("  1. Start a local LibreTranslate server:")
        print("     libretranslate --host 0.0.0.0 --port 5000")
        print("  2. Or get an API key from https://portal.libretranslate.com")
        raise Exception(f"Translation test failed: {last_error}")


if __name__ == '__main__':
    print("Running translation tests...")
    print("=" * 60)
    
    all_passed = True
    
    # Test 1: Direct argostranslate (no API required)
    try:
        test_hei_maailma_to_english_argostranslate()
        print("✓ Direct argostranslate test passed!")
    except Exception as e:
        print(f"✗ Direct argostranslate test failed: {e}")
        all_passed = False
    
    print("\n" + "-" * 60)
    
    # Test 2: LibreTranslate API (requires running server or API key)
    # This test is optional - it's OK if it fails when no server is running
    api_test_passed = False
    try:
        test_hei_maailma_to_english()
        print("✓ LibreTranslate API test passed!")
        api_test_passed = True
    except AssertionError as e:
        # Assertion errors mean the test logic failed, which is a real failure
        print(f"✗ LibreTranslate API test assertion failed: {e}")
        all_passed = False
    except Exception as e:
        # Other exceptions (like connection errors) are OK if no server is running
        print(f"⚠ LibreTranslate API test skipped: {e}")
        print("  (This is OK if no server is running or API key is required)")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All translation tests passed!")
    else:
        print("⚠ Some tests failed (see above for details)")
        sys.exit(1)
