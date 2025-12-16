#!/usr/bin/env python3
"""
translate_news.py - Translate HTML news articles to multiple languages
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from bs4 import BeautifulSoup

from translators.libretranslate import LibreTranslateTranslator
from translators.azure import AzureTranslator

# Constants
# Get script directory for relative paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Default paths
DEFAULT_RESPONSES_DIR = PROJECT_ROOT / 'responses'
DEFAULT_FILE = 'articles.html'
DEFAULT_LANGUAGES = ['sv', 'es', 'de', 'zh']  # Swedish, Spanish, German, Simplified Chinese
DEFAULT_TRANSLATOR = 'libretranslate'  # Translation provider
DEFAULT_SOURCE_LANG = 'fi'  # Finnish
DEFAULT_CONFIG = SCRIPT_DIR / 'config.yaml'

# CSS class names
CSS_CLASS_HIDDEN = 'hidden'
CSS_CLASS_ARTICLE_LANGUAGE_CONTROLS = 'article-language-controls'
CSS_CLASS_LANG_BTN = 'lang-btn'
CSS_CLASS_ACTIVE = 'active'
CSS_CLASS_ARTICLE_PARAGRAPH = 'article-paragraph'
CSS_CLASS_ORIGINAL_TEXT = 'original-text'
CSS_CLASS_TRANSLATION = 'translation'

# CSS styles
CSS_STYLES = """
.hidden { display: none; }

.article-language-controls { 
    margin: 20px 0; 
}

.article-language-controls button.lang-btn { 
    padding: 8px 16px; 
    margin-right: 8px;
    cursor: pointer;
    border: 1px solid #ccc;
    background-color: #f0f0f0;
    border-radius: 4px;
    font-size: 14px;
}

.article-language-controls button.lang-btn:hover {
    background-color: #e0e0e0;
}

.article-language-controls button.lang-btn.active {
    background-color: #0366d6;
    color: white;
    border: 1px solid #0366d6;
}

.article-paragraph {
    margin-bottom: 20px;
}

.article-paragraph .original-text {
    margin-bottom: 8px;
}

.article-paragraph .translation {
    margin-top: 8px;
    padding-left: 20px;
    font-style: italic;
    color: #555;
}
"""

# JavaScript code
JS_CODE = """
function toggleArticleLang(button, lang) {
    // Find the article element
    const article = button.closest('article');
    
    // Get all translation paragraphs in this article
    const allTranslations = article.querySelectorAll('.translation');
    
    // Check if this language is currently active
    const isActive = button.classList.contains('active');
    
    if (isActive) {
        // Hide all translations of this language
        allTranslations.forEach(el => {
            if (el.getAttribute('data-lang') === lang) {
                el.classList.add('hidden');
            }
        });
        button.classList.remove('active');
    } else {
        // Show all translations of this language
        allTranslations.forEach(el => {
            if (el.getAttribute('data-lang') === lang) {
                el.classList.remove('hidden');
            }
        });
        button.classList.add('active');
    }
}
"""


def get_newest_folder(responses_dir: Path) -> Path:
    """Get the newest folder from responses directory."""
    if not responses_dir.exists():
        raise FileNotFoundError(f"Responses directory not found: {responses_dir}")
    
    subdirs = [d for d in responses_dir.iterdir() 
               if d.is_dir() and not d.name.startswith('.')]
    
    if not subdirs:
        raise FileNotFoundError(f"No subdirectories found in {responses_dir}")
    
    # Get the newest folder by modification time
    newest = max(subdirs, key=lambda p: p.stat().st_mtime)
    return newest


def get_default_folder() -> Path:
    """Get the default folder (newest in responses directory) or None."""
    try:
        return get_newest_folder(DEFAULT_RESPONSES_DIR)
    except (FileNotFoundError, OSError):
        return None


def load_env_file(env_path: Path = None) -> dict:
    """
    Load environment variables from .env file.
    
    Args:
        env_path: Path to .env file (default: translator/.env)
        
    Returns:
        Dictionary of environment variables
    """
    if env_path is None:
        env_path = SCRIPT_DIR / '.env'
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


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_cache_dir(service_name: str, base_cache_dir: str = None) -> Path:
    """
    Get cache directory path for a specific translation service.
    
    Args:
        service_name: Name of the translation service (e.g., 'libretranslate')
        base_cache_dir: Base cache directory (default: translator/cache)
        
    Returns:
        Path to service-specific cache directory
    """
    if base_cache_dir is None:
        base_cache_dir = SCRIPT_DIR / 'cache'
    else:
        base_cache_dir = Path(base_cache_dir)
        if not base_cache_dir.is_absolute():
            base_cache_dir = SCRIPT_DIR / base_cache_dir
    
    cache_dir = base_cache_dir / service_name
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def cache_files_exist(cache_dir: Path, source_lang: str, target_langs: List[str]) -> bool:
    """
    Check if any cache files exist for the given language pairs.
    
    Args:
        cache_dir: Service-specific cache directory
        source_lang: Source language code
        target_langs: List of target language codes
        
    Returns:
        True if at least one cache file exists, False otherwise
    """
    for target_lang in target_langs:
        cache_file = get_cache_file_path(cache_dir, source_lang, target_lang)
        if cache_file.exists():
            return True
    return False


def get_cache_file_path(cache_dir: Path, source_lang: str, target_lang: str) -> Path:
    """
    Get cache file path for a language pair.
    
    Args:
        cache_dir: Service-specific cache directory
        source_lang: Source language code
        target_lang: Target language code
        
    Returns:
        Path to JSON cache file for this language pair
    """
    filename = f"translations_{source_lang}_{target_lang}.json"
    return cache_dir / filename


def load_cache_file(cache_file: Path) -> Dict[str, str]:
    """
    Load cache dictionary from JSON file.
    
    Args:
        cache_file: Path to JSON cache file
        
    Returns:
        Dictionary mapping text hash to translation, or empty dict if file doesn't exist
    """
    if not cache_file.exists():
        return {}
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load cache file {cache_file}: {e}. Starting with empty cache.", file=sys.stderr)
        return {}


def save_cache_file(cache_file: Path, cache: Dict[str, str]):
    """
    Save cache dictionary to JSON file.
    
    Args:
        cache_file: Path to JSON cache file
        cache: Dictionary mapping text hash to translation
    """
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Warning: Could not write cache file {cache_file}: {e}", file=sys.stderr)


def load_from_cache(cache_dir: Path, text_hash: str, source_lang: str, target_lang: str) -> Optional[str]:
    """
    Load translation from JSON cache file.
    
    Args:
        cache_dir: Service-specific cache directory
        text_hash: MD5 hash of source text
        source_lang: Source language code
        target_lang: Target language code
        
    Returns:
        Cached translation text, or None if not found
    """
    cache_file = get_cache_file_path(cache_dir, source_lang, target_lang)
    cache = load_cache_file(cache_file)
    return cache.get(text_hash)


def save_to_cache(cache_dir: Path, text_hash: str, source_lang: str, target_lang: str, translation: str):
    """
    Save translation to JSON cache file.
    
    Args:
        cache_dir: Service-specific cache directory
        text_hash: MD5 hash of source text
        source_lang: Source language code
        target_lang: Target language code
        translation: Translated text to cache
    """
    cache_file = get_cache_file_path(cache_dir, source_lang, target_lang)
    cache = load_cache_file(cache_file)
    cache[text_hash] = translation
    save_cache_file(cache_file, cache)


def get_text_hash(text: str) -> str:
    """
    Generate hash for text to use as cache key.
    
    Note: MD5 is used here for cache key generation only (not cryptographic purposes).
    While MD5 has known cryptographic weaknesses, it's sufficient for cache keys
    where collision resistance is not a security concern.
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()


class TranslationStats:
    """Track translation statistics."""
    def __init__(self):
        self.chars_translated = 0  # Characters sent to API
        self.chars_cached = 0  # Characters retrieved from cache
        self.words_translated = 0  # Words sent to API (approximate)
        self.words_cached = 0  # Words retrieved from cache (approximate)
        self.api_calls = 0  # Number of API calls made
        self.cache_hits = 0  # Number of cache hits
        self.provider = None
    
    def count_words(self, text: str) -> int:
        """Approximate word count (split on whitespace)."""
        return len(text.split())
    
    def add_translation(self, text: str, from_cache: bool):
        """Add translation statistics."""
        chars = len(text)
        words = self.count_words(text)
        
        if from_cache:
            self.chars_cached += chars
            self.words_cached += words
            self.cache_hits += 1
        else:
            self.chars_translated += chars
            self.words_translated += words
            self.api_calls += 1
    
    def write_log(self, log_path: Path):
        """Write statistics to log file."""
        total_chars = self.chars_translated + self.chars_cached
        total_words = self.words_translated + self.words_cached
        
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"Translation Statistics\n")
            f.write(f"{'=' * 50}\n")
            f.write(f"Provider: {self.provider or 'unknown'}\n")
            f.write(f"\n")
            f.write(f"Characters:\n")
            f.write(f"  Translated via API: {self.chars_translated:,}\n")
            f.write(f"  Retrieved from cache: {self.chars_cached:,}\n")
            f.write(f"  Total: {total_chars:,}\n")
            f.write(f"\n")
            f.write(f"Words (approximate):\n")
            f.write(f"  Translated via API: {self.words_translated:,}\n")
            f.write(f"  Retrieved from cache: {self.words_cached:,}\n")
            f.write(f"  Total: {total_words:,}\n")
            f.write(f"\n")
            f.write(f"API Calls: {self.api_calls:,}\n")
            f.write(f"Cache Hits: {self.cache_hits:,}\n")
            if total_chars > 0:
                cache_ratio = (self.chars_cached / total_chars) * 100
                f.write(f"Cache Hit Rate: {cache_ratio:.1f}%\n")


def translate_with_cache(translator, text: str, source_lang: str, target_lang: str, 
                         cache_dir: Optional[Path] = None, stats: Optional[TranslationStats] = None) -> str:
    """
    Translate text using JSON cache if available.
    
    Args:
        translator: Translator instance
        text: Text to translate
        source_lang: Source language code
        target_lang: Target language code
        cache_dir: Service-specific cache directory (None if caching disabled)
        stats: Optional TranslationStats object to track statistics
        
    Returns:
        Translated text
    """
    text_hash = get_text_hash(text)
    
    # Check cache if enabled
    if cache_dir is not None:
        cached_translation = load_from_cache(cache_dir, text_hash, source_lang, target_lang)
        if cached_translation is not None:
            if stats:
                stats.add_translation(text, from_cache=True)
            return cached_translation
    
    # Translate
    translation = translator.translate(text, target_lang)
    
    # Save to cache if enabled
    if cache_dir is not None:
        save_to_cache(cache_dir, text_hash, source_lang, target_lang, translation)
    
    if stats:
        stats.add_translation(text, from_cache=False)
    
    return translation


def parse_html(html_path: str) -> BeautifulSoup:
    """Parse HTML file."""
    with open(html_path, 'r', encoding='utf-8') as f:
        return BeautifulSoup(f.read(), 'html.parser')


def translate_articles(soup: BeautifulSoup, translator, target_langs: List[str], 
                       cache_dir: Optional[Path], source_lang: str, stats: Optional[TranslationStats] = None) -> BeautifulSoup:
    """
    Translate articles in HTML and add language controls.
    
    Args:
        soup: BeautifulSoup object
        translator: Translator instance
        target_langs: List of target language codes
        cache_dir: Service-specific cache directory
        source_lang: Source language code
        
    Returns:
        Modified BeautifulSoup object
    """
    # Find all articles
    articles = soup.find_all('article')
    
    print(f"Found {len(articles)} articles to process")
    
    for article_idx, article in enumerate(articles, 1):
        print(f"\nProcessing article {article_idx}/{len(articles)}")
        
        # Add language toggle buttons at the top of the article (only for target languages)
        controls = soup.new_tag('div', **{'class': CSS_CLASS_ARTICLE_LANGUAGE_CONTROLS})
        
        # Buttons for target languages only (no Finnish button)
        for lang in target_langs:
            btn = soup.new_tag('button', **{
                'class': CSS_CLASS_LANG_BTN,
                'data-lang': lang,
                'onclick': f"toggleArticleLang(this, '{lang}')"
            })
            btn.string = get_language_name(lang)
            controls.append(btn)
        
        # Insert controls at the beginning of the article (after header if it exists)
        header = article.find('header')
        if header:
            header.insert_after(controls)
        else:
            article.insert(0, controls)
        
        # Find all paragraphs in the article's section
        section = article.find('section')
        if section:
            paragraphs = section.find_all('p')
            
            for para_idx, p in enumerate(paragraphs, 1):
                text = p.get_text(strip=True)
                if not text:
                    continue
                
                print(f"  Translating section paragraph {para_idx}/{len(paragraphs)}...")
                
                # Create container for this paragraph and its translations
                container = soup.new_tag('div', **{'class': CSS_CLASS_ARTICLE_PARAGRAPH})
                
                # Add original paragraph (always visible, no data-lang or hidden class)
                original_p = soup.new_tag('p', **{'class': CSS_CLASS_ORIGINAL_TEXT})
                original_p.string = text
                container.append(original_p)
                
                # Translate to each target language
                for lang in target_langs:
                    print(f"    -> {lang}", end='', flush=True)
                    translation = translate_with_cache(translator, text, source_lang, lang, cache_dir, stats)
                    print(f" ✓")
                    
                    # Add translated paragraph (hidden by default)
                    translated_p = soup.new_tag('p', **{
                        'class': f'{CSS_CLASS_TRANSLATION} translation-{lang} {CSS_CLASS_HIDDEN}',
                        'data-lang': lang
                    })
                    translated_p.string = translation
                    container.append(translated_p)
                
                # Replace original paragraph with container
                p.replace_with(container)
        
        # Also translate paragraphs in full-article-content divs
        full_article_divs = article.find_all('div', class_='full-article-content')
        for full_article_div in full_article_divs:
            paragraphs = full_article_div.find_all('p')
            
            for para_idx, p in enumerate(paragraphs, 1):
                text = p.get_text(strip=True)
                if not text:
                    continue
                
                print(f"  Translating full article paragraph {para_idx}/{len(paragraphs)}...")
                
                # Create container for this paragraph and its translations
                container = soup.new_tag('div', **{'class': CSS_CLASS_ARTICLE_PARAGRAPH})
                
                # Add original paragraph (always visible, no data-lang or hidden class)
                original_p = soup.new_tag('p', **{'class': CSS_CLASS_ORIGINAL_TEXT})
                original_p.string = text
                container.append(original_p)
                
                # Translate to each target language
                for lang in target_langs:
                    print(f"    -> {lang}", end='', flush=True)
                    translation = translate_with_cache(translator, text, source_lang, lang, cache_dir, stats)
                    print(f" ✓")
                    
                    # Add translated paragraph (hidden by default)
                    translated_p = soup.new_tag('p', **{
                        'class': f'{CSS_CLASS_TRANSLATION} translation-{lang} {CSS_CLASS_HIDDEN}',
                        'data-lang': lang
                    })
                    translated_p.string = translation
                    container.append(translated_p)
                
                # Replace original paragraph with container
                p.replace_with(container)
    
    return soup


def get_language_name(lang_code: str) -> str:
    """Get display name for language code."""
    names = {
        'fi': 'Suomi',
        'en': 'English',
        'sv': 'Svenska',
        'es': 'Español',
        'de': 'Deutsch',
        'zh': '中文',
        'zh-CN': '简体中文',
        'zh-Hans': '简体中文'
    }
    return names.get(lang_code, lang_code.upper())


def add_styles_and_scripts(soup: BeautifulSoup) -> BeautifulSoup:
    """Add CSS styles and JavaScript for language switching."""
    # Add CSS
    style = soup.new_tag('style')
    style.string = CSS_STYLES
    
    head = soup.find('head')
    if head:
        head.append(style)
    
    # Add JavaScript
    script = soup.new_tag('script')
    script.string = JS_CODE
    
    body = soup.find('body')
    if body:
        body.append(script)
    
    return soup


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Translate HTML news articles to multiple languages'
    )
    
    # Determine default input path
    default_folder = get_default_folder()
    if default_folder:
        default_input = str(default_folder / DEFAULT_FILE)
    else:
        default_input = str(SCRIPT_DIR / 'examples' / 'sample_articles.html')
    
    parser.add_argument(
        '--input', '-i',
        default=default_input,
        help=f'Input HTML file path (default: {default_input})'
    )
    parser.add_argument(
        '--output', '-o',
        default=None,
        help='Output HTML file path (default: same as input with _translated suffix)'
    )
    parser.add_argument(
        '--config', '-c',
        default=str(DEFAULT_CONFIG),
        help=f'Configuration file path (default: {DEFAULT_CONFIG})'
    )
    parser.add_argument(
        '--languages', '-l',
        nargs='+',
        default=DEFAULT_LANGUAGES,
        help=f'Target languages (default: {", ".join(DEFAULT_LANGUAGES)})'
    )
    parser.add_argument(
        '--translator', '-t',
        default=DEFAULT_TRANSLATOR,
        help=f'Translation provider (default: {DEFAULT_TRANSLATOR})'
    )
    parser.add_argument(
        '--source-lang', '-s',
        default=DEFAULT_SOURCE_LANG,
        help=f'Source language code (default: {DEFAULT_SOURCE_LANG})'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable translation cache (default: use cache if cache files exist)'
    )
    
    args = parser.parse_args()
    
    # Resolve paths
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = SCRIPT_DIR / config_path
    
    input_path = Path(args.input)
    if not input_path.is_absolute():
        # Try relative to script dir first, then as absolute path
        if (SCRIPT_DIR / input_path).exists():
            input_path = SCRIPT_DIR / input_path
        else:
            input_path = Path(input_path).resolve()
    
    # Default output path
    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = SCRIPT_DIR / output_path
    else:
        # Create output path with _translated suffix
        output_path = input_path.parent / f"{input_path.stem}_translated{input_path.suffix}"
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load configuration (create default if doesn't exist)
    if config_path.exists():
        print(f"Loading configuration from {config_path}")
        config = load_config(str(config_path))
    else:
        print(f"Config file not found at {config_path}, using defaults")
        config = {}
    
    # Override config with command line arguments
    if 'translation' not in config:
        config['translation'] = {}
    config['translation']['provider'] = args.translator
    config['translation']['source_language'] = args.source_lang
    config['translation']['target_languages'] = args.languages
    
    # Initialize translator
    provider = config['translation']['provider']
    source_lang = config['translation']['source_language']
    target_langs = config['translation']['target_languages']
    
    # Setup cache (after provider is known)
    # Default: use cache if cache files exist, unless explicitly disabled
    cache_config = config.get('cache', {})
    cache_explicitly_disabled = args.no_cache or cache_config.get('enabled', None) is False
    
    cache_dir = None
    if not cache_explicitly_disabled:
        cache_base_dir = cache_config.get('dir', 'cache')
        cache_dir = get_cache_dir(provider, cache_base_dir)
        
        # Check if cache files exist (default behavior: enable if files exist)
        cache_enabled_in_config = cache_config.get('enabled', None)
        if cache_enabled_in_config is None:
            # Default: enable cache if files exist
            if cache_files_exist(cache_dir, source_lang, target_langs):
                print(f"Cache files found. Using cache directory: {cache_dir}")
            else:
                print(f"No cache files found. Cache disabled. Cache directory: {cache_dir}")
                cache_dir = None
        elif cache_enabled_in_config:
            print(f"Cache enabled by config. Using cache directory: {cache_dir}")
        else:
            print("Cache disabled by config.")
            cache_dir = None
    else:
        print("Cache disabled by command-line option or config.")
    
    print(f"Initializing {provider} translator")
    print(f"Source language: {source_lang}")
    print(f"Target languages: {', '.join(target_langs)}")
    
    # Initialize translation statistics
    stats = TranslationStats()
    stats.provider = provider
    
    if provider == 'libretranslate':
        translator_config = config.get('libretranslate', {})
        # Set defaults if not in config
        translator_config.setdefault('api_url', 'https://libretranslate.com/translate')
        translator = LibreTranslateTranslator(
            source_lang=source_lang,
            target_langs=target_langs,
            **translator_config
        )
    elif provider == 'azure':
        translator_config = config.get('azure', {})
        
        # Load .env file to get Azure credentials
        env_vars = load_env_file()
        
        # Get subscription key from .env or config
        subscription_key = translator_config.get('subscription_key')
        if not subscription_key:
            # Try to get from .env file
            subscription_key = env_vars.get('AZURE_TRANSLATOR_KEY1') or env_vars.get('AZURE_TRANSLATOR_KEY')
            if subscription_key:
                print("Loaded Azure subscription key from .env file")
        
        if not subscription_key:
            print("Error: Azure Translator requires subscription_key. Set it in config.yaml or .env file as AZURE_TRANSLATOR_KEY1", file=sys.stderr)
            sys.exit(1)
        
        # Set defaults if not in config
        translator_config.setdefault('endpoint', 'https://api.cognitive.microsofttranslator.com/')
        translator_config.setdefault('region', env_vars.get('AZURE_TRANSLATOR_REGION', 'westeurope'))
        translator_config.setdefault('timeout', 30)
        translator_config.setdefault('max_retries', 3)
        translator_config.setdefault('retry_delay', 2)
        
        # Override with subscription key from .env if available
        translator_config['subscription_key'] = subscription_key
        
        translator = AzureTranslator(
            source_lang=source_lang,
            target_langs=target_langs,
            **translator_config
        )
    else:
        print(f"Error: Unknown provider '{provider}'", file=sys.stderr)
        sys.exit(1)
    
    # Parse HTML
    print(f"\nParsing HTML from {input_path}")
    soup = parse_html(str(input_path))
    
    # Translate articles
    print("\nStarting translation...")
    soup = translate_articles(soup, translator, target_langs, cache_dir, source_lang, stats)
    
    # Add styles and scripts
    print("\nAdding styles and scripts...")
    soup = add_styles_and_scripts(soup)
    
    # Cache is automatically saved during translation (JSON-based)
    if cache_dir is not None:
        print(f"\nCache saved to {cache_dir}")
    
    # Write output
    print(f"\nWriting output to {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(str(soup.prettify()))
    
    # Write translation statistics log
    log_path = output_path.parent / f"{output_path.stem}_stats.txt"
    stats.write_log(log_path)
    print(f"\nTranslation statistics saved to: {log_path}")
    
    print("\n✓ Translation complete!")
    print(f"Output saved to: {output_path}")


if __name__ == '__main__':
    main()
