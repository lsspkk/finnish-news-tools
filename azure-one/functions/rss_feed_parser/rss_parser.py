import feedparser
import logging
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Dict, List, Any

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


def parse_rss_feed(feed_url: str, add_origin_rss_suffix: bool = True, cache_ttl_hours: int = 1) -> Dict[str, Any]:
    logger.info(f"Fetching RSS feed from {feed_url}")
    feed = feedparser.parse(feed_url)
    
    if feed.bozo:
        logger.warning(f"Feed parsing warnings: {feed.bozo_exception}")
    
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=cache_ttl_hours)
    
    feed_metadata = {
        'title': feed.feed.get('title', ''),
        'description': feed.feed.get('description', ''),
        'link': feed.feed.get('link', ''),
        'language': feed.feed.get('language', 'fi'),
        'last_build_date': feed.feed.get('updated', ''),
        'fetch_timestamp': now.isoformat()
    }
    
    items = []
    for entry in feed.entries:
        link = entry.get('link', '')
        
        if add_origin_rss_suffix:
            link = add_origin_rss(link)
        
        shortcode = extract_shortcode(link)
        
        item = {
            'title': entry.get('title', ''),
            'link': link,
            'description': entry.get('description', ''),
            'guid': entry.get('id', link),
            'pub_date': entry.get('published', ''),
            'categories': [cat.get('term', '') for cat in entry.get('tags', [])],
            'shortcode': shortcode
        }
        items.append(item)
    
    result = {
        'feed_metadata': feed_metadata,
        'items': items,
        'expires_at': expires_at.isoformat(),
        'cache_ttl_hours': cache_ttl_hours
    }
    
    logger.info(f"Parsed {len(items)} items from RSS feed")
    return result
