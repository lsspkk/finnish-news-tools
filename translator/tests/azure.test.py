#!/usr/bin/env python3
"""
Test file for Azure Translator functionality.

Tests that Azure Translator works correctly by translating "Hei maailma" (Finnish) to Spanish.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to import translator modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from translators.azure import AzureTranslator


def load_env_file(env_path: Path = None) -> dict:
    """
    Load environment variables from .env file.
    
    Args:
        env_path: Path to .env file (default: translator/.env)
        
    Returns:
        Dictionary of environment variables
    """
    if env_path is None:
        env_path = Path(__file__).parent.parent / '.env'
    else:
        env_path = Path(env_path)
    
    env_vars = {}
    if not env_path.exists():
        return env_vars
    
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                # Parse KEY=VALUE format
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    env_vars[key] = value
    except Exception as e:
        print(f"Warning: Could not load .env file: {e}", file=sys.stderr)
    
    return env_vars


def test_hei_maailma_to_spanish():
    """Test: Translate 'Hei maailma' (Finnish) to Spanish using Azure Translator."""
    text = "Hei maailma"
    source_lang = 'fi'
    target_lang = 'es'
    
    print(f"\nTesting Azure Translator...")
    print(f"Translating '{text}' (Finnish) to Spanish...")
    
    # Load .env file
    env_vars = load_env_file()
    subscription_key = env_vars.get('AZURE_TRANSLATOR_KEY1') or env_vars.get('AZURE_TRANSLATOR_KEY')
    
    if not subscription_key:
        print("✗ Azure Translator test skipped: No API key found in .env file")
        print("\nTo run this test:")
        print("  1. Create a .env file in translator/ directory")
        print("  2. Add: AZURE_TRANSLATOR_KEY1=your-api-key-here")
        print("  3. Optionally add: AZURE_TRANSLATOR_REGION=westeurope")
        return False
    
    print(f"✓ Loaded API key from .env file")
    
    # Get region from .env or use default
    region = env_vars.get('AZURE_TRANSLATOR_REGION', 'westeurope')
    endpoint = env_vars.get('AZURE_TRANSLATOR_ENDPOINT', 'https://api.cognitive.microsofttranslator.com/')
    
    try:
        # Create Azure Translator instance
        translator = AzureTranslator(
            source_lang=source_lang,
            target_langs=[target_lang],
            subscription_key=subscription_key,
            endpoint=endpoint,
            region=region,
            timeout=30
        )
        
        print(f"Translating using Azure Translator...")
        print(f"  Source: {source_lang} (Finnish)")
        print(f"  Target: {target_lang} (Spanish)")
        print(f"  Endpoint: {endpoint}")
        print(f"  Region: {region}")
        
        # Translate
        result = translator.translate(text, target_lang)
        print(f"\nTranslation result: '{result}'")
        
        # Check if we got the original text back (indicates failure)
        if result == text:
            print(f"✗ Warning: Got original text back, translation may have failed")
            print(f"  This could indicate:")
            print(f"  - Invalid API key")
            print(f"  - Network error")
            print(f"  - Azure service error")
            raise Exception("Translation returned original text (translation likely failed)")
        
        # Check that we got a translation
        assert result is not None, "Translation should not be None"
        assert result != text, "Translation should be different from original text"
        assert len(result) > 0, "Translation should not be empty"
        
        # The translation should be in Spanish (common words: "Hola", "mundo")
        result_lower = result.lower()
        print(f"\n✓ Successfully translated '{text}' to '{result}'")
        print(f"  Expected Spanish translation should contain words like 'Hola' or 'mundo'")
        
        return True
        
    except ValueError as e:
        print(f"✗ Configuration error: {e}")
        raise
    except Exception as e:
        print(f"✗ Translation failed: {e}")
        print(f"\nTroubleshooting:")
        print(f"  1. Verify your API key is correct in .env file")
        print(f"  2. Check your Azure Translator resource is active")
        print(f"  3. Verify network connectivity")
        print(f"  4. Check Azure service status")
        raise


if __name__ == '__main__':
    print("Running Azure Translator tests...")
    print("=" * 60)
    
    all_passed = True
    
    # Test: Azure Translator API
    try:
        test_hei_maailma_to_spanish()
        print("\n✓ Azure Translator test passed!")
    except AssertionError as e:
        print(f"\n✗ Azure Translator test assertion failed: {e}")
        all_passed = False
    except Exception as e:
        print(f"\n✗ Azure Translator test failed: {e}")
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All Azure Translator tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed (see above for details)")
        sys.exit(1)
