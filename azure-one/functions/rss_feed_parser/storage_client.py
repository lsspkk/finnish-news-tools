import os
import logging
from typing import Optional, Dict, Any
try:
    from ..shared.storage_factory import get_blob_storage
except ImportError:
    from shared.storage_factory import get_blob_storage

logger = logging.getLogger(__name__)


class StorageClient:
    def __init__(self):
        self.storage = get_blob_storage()
        self.container_name = os.getenv('STORAGE_CONTAINER', 'finnish-news-tools')
        logger.info(f"Initialized StorageClient with container {self.container_name}")
    
    def save_rss_feed(self, feed_data: Dict[str, Any], blob_path: str):
        use_local = os.getenv('USE_LOCAL_STORAGE', 'false').lower() == 'true'
        
        if use_local:
            self.storage.save_file(blob_path, feed_data)
        else:
            container = self.storage.get_container_client(self.container_name)
            blob_client = container.get_blob_client(blob_path)
            import json
            blob_client.upload_blob(
                json.dumps(feed_data, indent=2, ensure_ascii=False),
                overwrite=True,
                encoding='utf-8'
            )
        
        logger.info(f"Saved RSS feed to {blob_path}")
    
    def check_rss_feed_exists(self, blob_path: str) -> bool:
        use_local = os.getenv('USE_LOCAL_STORAGE', 'false').lower() == 'true'
        
        if use_local:
            return self.storage.file_exists(blob_path)
        else:
            container = self.storage.get_container_client(self.container_name)
            blob_client = container.get_blob_client(blob_path)
            try:
                blob_client.get_blob_properties()
                return True
            except Exception:
                return False
    
    def get_rss_feed(self, blob_path: str) -> Optional[Dict[str, Any]]:
        use_local = os.getenv('USE_LOCAL_STORAGE', 'false').lower() == 'true'
        
        if use_local:
            return self.storage.read_file(blob_path)
        else:
            container = self.storage.get_container_client(self.container_name)
            blob_client = container.get_blob_client(blob_path)
            try:
                import json
                blob_data = blob_client.download_blob().readall()
                return json.loads(blob_data.decode('utf-8'))
            except Exception as e:
                logger.debug(f"Could not read RSS feed from {blob_path}: {e}")
                return None
    
    def get_cache_status(self) -> Dict[str, Any]:
        blob_path = 'cache/yle/paauutiset.json'
        exists = self.check_rss_feed_exists(blob_path)
        feed_data = self.get_rss_feed(blob_path) if exists else None
        
        return {
            "rss_feed_path": blob_path,
            "rss_feed_exists": exists,
            "rss_feed_items_count": len(feed_data.get('items', [])) if feed_data else 0,
            "rss_feed_title": feed_data.get('feed_metadata', {}).get('title', '') if feed_data else '',
            "rss_feed_last_fetch": feed_data.get('feed_metadata', {}).get('fetch_timestamp', '') if feed_data else ''
        }
