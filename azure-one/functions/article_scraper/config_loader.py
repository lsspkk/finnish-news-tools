import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


def load_scraper_config() -> Dict[str, Any]:
    use_local = os.getenv('USE_LOCAL_STORAGE', 'false').lower() == 'true'
    
    if use_local:
        config_path = os.getenv('SCRAPER_CONFIG_PATH', 'scraper-config.yaml.local')
    else:
        config_path = os.getenv('SCRAPER_CONFIG_PATH', 'scraper-config.yaml')
    
    if not os.path.exists(config_path):
        logger.warning(f"Config file not found at {config_path}, using defaults")
        return get_default_config()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded scraper config from {config_path}")
        return config.get('scraping', {})
    except Exception as e:
        logger.error(f"Error loading config: {e}, using defaults")
        return get_default_config()


def get_default_config() -> Dict[str, Any]:
    return {
        'selectors': {
            'title': ['h1.article-title', 'h1', 'article h1', '.article-header h1', 'title'],
            'paragraphs': ['article p', '.article-content p', '.article-body p', 'main p', '.content p'],
            'exclude': ['.advertisement', '.social-share', '.related-articles', 'footer', 'nav', 'script', 'style']
        },
        'cleaning': {
            'remove_empty': True,
            'min_length': 20,
            'strip_whitespace': True,
            'remove_newlines': False
        },
        'url': {
            'add_origin_rss': True,
            'remove_existing_params': False
        },
        'request': {
            'timeout': 30,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            'follow_redirects': True,
            'max_redirects': 5
        }
    }
