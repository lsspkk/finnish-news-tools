#!/usr/bin/env python3
"""
translate_news.py - Translate HTML news articles to multiple languages
"""
import argparse
import json
import hashlib
import os
import sys
from pathlib import Path
from typing import Dict, List

import yaml
from bs4 import BeautifulSoup

from translators.libretranslate import LibreTranslateTranslator


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_cache(cache_path: str) -> dict:
    """Load translation cache from JSON file."""
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print(f"Warning: Could not load cache from {cache_path}. Starting with empty cache.")
            return {}
    return {}


def save_cache(cache_path: str, cache: dict):
    """Save translation cache to JSON file."""
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def get_text_hash(text: str) -> str:
    """Generate hash for text to use as cache key."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def translate_with_cache(translator, text: str, target_lang: str, cache: dict) -> str:
    """
    Translate text using cache if available.
    
    Args:
        translator: Translator instance
        text: Text to translate
        target_lang: Target language code
        cache: Translation cache dictionary
        
    Returns:
        Translated text
    """
    text_hash = get_text_hash(text)
    
    # Check cache
    if text_hash in cache and target_lang in cache[text_hash]:
        return cache[text_hash][target_lang]
    
    # Translate
    translation = translator.translate(text, target_lang)
    
    # Save to cache
    if text_hash not in cache:
        cache[text_hash] = {}
    cache[text_hash][target_lang] = translation
    
    return translation


def parse_html(html_path: str) -> BeautifulSoup:
    """Parse HTML file."""
    with open(html_path, 'r', encoding='utf-8') as f:
        return BeautifulSoup(f.read(), 'html.parser')


def translate_articles(soup: BeautifulSoup, translator, target_langs: List[str], 
                       cache: dict, source_lang: str) -> BeautifulSoup:
    """
    Translate articles in HTML and add language controls.
    
    Args:
        soup: BeautifulSoup object
        translator: Translator instance
        target_langs: List of target language codes
        cache: Translation cache
        source_lang: Source language code
        
    Returns:
        Modified BeautifulSoup object
    """
    # Find all articles
    articles = soup.find_all('article')
    
    print(f"Found {len(articles)} articles to process")
    
    for article_idx, article in enumerate(articles, 1):
        print(f"\nProcessing article {article_idx}/{len(articles)}")
        
        # Find all paragraphs in the article's section
        section = article.find('section')
        if not section:
            continue
        
        paragraphs = section.find_all('p')
        
        for para_idx, p in enumerate(paragraphs, 1):
            text = p.get_text(strip=True)
            if not text:
                continue
            
            print(f"  Translating paragraph {para_idx}/{len(paragraphs)}...")
            
            # Create container for this paragraph and its translations
            container = soup.new_tag('div', **{'class': 'article-paragraph'})
            
            # Add original paragraph with data-lang attribute
            original_p = soup.new_tag('p', **{'data-lang': source_lang})
            original_p.string = text
            container.append(original_p)
            
            # Translate to each target language
            for lang in target_langs:
                print(f"    -> {lang}", end='', flush=True)
                translation = translate_with_cache(translator, text, lang, cache)
                print(f" ✓")
                
                # Add translated paragraph (hidden by default)
                translated_p = soup.new_tag('p', **{
                    'data-lang': lang,
                    'class': 'hidden'
                })
                translated_p.string = translation
                container.append(translated_p)
            
            # Add language toggle buttons
            controls = soup.new_tag('div', **{'class': 'translation-controls'})
            
            # Button for source language (active by default)
            btn_source = soup.new_tag('button', **{
                'class': 'active',
                'onclick': f"showLang(this, '{source_lang}')"
            })
            btn_source.string = get_language_name(source_lang)
            controls.append(btn_source)
            
            # Buttons for target languages
            for lang in target_langs:
                btn = soup.new_tag('button', **{
                    'onclick': f"showLang(this, '{lang}')"
                })
                btn.string = get_language_name(lang)
                controls.append(btn)
            
            container.append(controls)
            
            # Replace original paragraph with container
            p.replace_with(container)
    
    return soup


def get_language_name(lang_code: str) -> str:
    """Get display name for language code."""
    names = {
        'fi': 'Suomi',
        'en': 'English',
        'sv': 'Svenska'
    }
    return names.get(lang_code, lang_code.upper())


def add_styles_and_scripts(soup: BeautifulSoup) -> BeautifulSoup:
    """Add CSS styles and JavaScript for language switching."""
    
    # Add CSS
    style = soup.new_tag('style')
    style.string = """
.hidden { display: none; }
.translation-controls { 
    margin: 10px 0; 
}
.translation-controls button { 
    padding: 5px 10px; 
    margin-right: 5px;
    cursor: pointer;
    border: 1px solid #ccc;
    background-color: #f0f0f0;
    border-radius: 3px;
}
.translation-controls button:hover {
    background-color: #e0e0e0;
}
.translation-controls button.active {
    background-color: #0366d6;
    color: white;
    border: 1px solid #0366d6;
}
.article-paragraph {
    margin-bottom: 20px;
}
"""
    
    head = soup.find('head')
    if head:
        head.append(style)
    
    # Add JavaScript
    script = soup.new_tag('script')
    script.string = """
function showLang(button, lang) {
    const container = button.closest('.article-paragraph');
    const allLangs = container.querySelectorAll('[data-lang]');
    allLangs.forEach(el => el.classList.add('hidden'));
    const targetLang = container.querySelector('[data-lang="' + lang + '"]');
    targetLang.classList.remove('hidden');
    
    const buttons = container.querySelectorAll('button');
    buttons.forEach(btn => btn.classList.remove('active'));
    button.classList.add('active');
}
"""
    
    body = soup.find('body')
    if body:
        body.append(script)
    
    return soup


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Translate HTML news articles to multiple languages'
    )
    parser.add_argument(
        '--input', '-i',
        default='examples/sample_articles.html',
        help='Input HTML file path'
    )
    parser.add_argument(
        '--output', '-o',
        default='examples/translated_articles.html',
        help='Output HTML file path'
    )
    parser.add_argument(
        '--config', '-c',
        default='config.yaml',
        help='Configuration file path'
    )
    
    args = parser.parse_args()
    
    # Get script directory for relative paths
    script_dir = Path(__file__).parent
    
    # Resolve paths relative to script directory
    config_path = script_dir / args.config
    input_path = script_dir / args.input
    output_path = script_dir / args.output
    
    # Load configuration
    print(f"Loading configuration from {config_path}")
    config = load_config(str(config_path))
    
    # Setup cache
    cache = {}
    cache_enabled = config.get('cache', {}).get('enabled', True)
    if cache_enabled:
        cache_file = config.get('cache', {}).get('file', 'cache/translations.json')
        cache_path = script_dir / cache_file
        print(f"Loading cache from {cache_path}")
        cache = load_cache(str(cache_path))
    
    # Initialize translator
    provider = config['translation']['provider']
    source_lang = config['translation']['source_language']
    target_langs = config['translation']['target_languages']
    
    print(f"Initializing {provider} translator")
    print(f"Source language: {source_lang}")
    print(f"Target languages: {', '.join(target_langs)}")
    
    if provider == 'libretranslate':
        translator_config = config.get('libretranslate', {})
        translator = LibreTranslateTranslator(
            source_lang=source_lang,
            target_langs=target_langs,
            **translator_config
        )
    else:
        print(f"Error: Unknown provider '{provider}'")
        sys.exit(1)
    
    # Parse HTML
    print(f"\nParsing HTML from {input_path}")
    soup = parse_html(str(input_path))
    
    # Translate articles
    print("\nStarting translation...")
    soup = translate_articles(soup, translator, target_langs, cache, source_lang)
    
    # Add styles and scripts
    print("\nAdding styles and scripts...")
    soup = add_styles_and_scripts(soup)
    
    # Save cache
    if cache_enabled:
        print(f"\nSaving cache to {cache_path}")
        save_cache(str(cache_path), cache)
    
    # Write output
    print(f"\nWriting output to {output_path}")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(str(soup.prettify()))
    
    print("\n✓ Translation complete!")
    print(f"Output saved to: {output_path}")


if __name__ == '__main__':
    main()
