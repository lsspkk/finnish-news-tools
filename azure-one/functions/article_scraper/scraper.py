import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def extract_shortcode(url: str) -> str:
    if '/a/' in url:
        return url.split('/a/')[-1].split('?')[0].split('#')[0]
    return ''


def add_origin_rss(url: str) -> str:
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    if 'origin' not in query_params:
        query_params['origin'] = ['rss']
    
    new_query = urlencode(query_params, doseq=True)
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))


def clean_text(text: str, config: Dict[str, Any]) -> Optional[str]:
    cleaning = config.get('cleaning', {})
    
    if cleaning.get('strip_whitespace', True):
        text = text.strip()
    
    if cleaning.get('remove_empty', True) and not text:
        return None
    
    min_length = cleaning.get('min_length', 0)
    if len(text) < min_length:
        return None
    
    if cleaning.get('normalize_spaces', False):
        import re
        text = re.sub(r'\s+', ' ', text)
    
    return text


def scrape_article(url: str, config: Dict[str, Any], language_code: str = 'fi', cache_ttl_hours: int = 1) -> Dict[str, Any]:
    logger.info(f"Scraping article from {url}")
    
    request_config = config.get('request', {})
    headers = request_config.get('headers', {})
    timeout = request_config.get('timeout', 30)
    
    url_config = config.get('url', {})
    if url_config.get('add_origin_rss', True):
        url = add_origin_rss(url)
    
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=request_config.get('follow_redirects', True)
        )
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        raise
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    for exclude_selector in config.get('selectors', {}).get('exclude', []):
        for element in soup.select(exclude_selector):
            element.decompose()
    
    title = None
    for title_selector in config.get('selectors', {}).get('title', []):
        title_elem = soup.select_one(title_selector)
        if title_elem:
            title = title_elem.get_text(strip=True)
            break
    
    if not title:
        title = soup.find('title')
        if title:
            title = title.get_text(strip=True)
    
    paragraphs = []
    for para_selector in config.get('selectors', {}).get('paragraphs', []):
        para_elems = soup.select(para_selector)
        if para_elems:
            for para_elem in para_elems:
                text = para_elem.get_text(separator=' ', strip=True)
                cleaned = clean_text(text, config)
                if cleaned:
                    paragraphs.append(cleaned)
            if paragraphs:
                break
    
    shortcode = extract_shortcode(url)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=cache_ttl_hours)
    
    result = {
        'url': url,
        'shortcode': shortcode,
        'title': title or '',
        'paragraphs': paragraphs,
        'scraped_at': now.isoformat(),
        'scraper_version': '1.0',
        'expires_at': expires_at.isoformat(),
        'cache_ttl_hours': cache_ttl_hours
    }
    
    logger.info(f"Scraped article {shortcode}: {len(paragraphs)} paragraphs")
    return result
