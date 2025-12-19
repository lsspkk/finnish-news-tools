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
    
    def save_article(self, article_data: Dict[str, Any], blob_path: str):
        use_local = os.getenv('USE_LOCAL_STORAGE', 'false').lower() == 'true'
        
        if use_local:
            self.storage.save_file(blob_path, article_data)
        else:
            container = self.storage.get_container_client(self.container_name)
            blob_client = container.get_blob_client(blob_path)
            import json
            blob_client.upload_blob(
                json.dumps(article_data, indent=2, ensure_ascii=False),
                overwrite=True,
                encoding='utf-8'
            )
        
        logger.info(f"Saved article to {blob_path}")
    
    def check_article_exists(self, blob_path: str) -> bool:
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
    
    def get_article(self, blob_path: str) -> Optional[Dict[str, Any]]:
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
                logger.debug(f"Could not read article from {blob_path}: {e}")
                return None
    
    def list_articles(self, prefix: str = 'cache/yle/articles/') -> list:
        use_local = os.getenv('USE_LOCAL_STORAGE', 'false').lower() == 'true'
        
        if use_local:
            files = self.storage.list_files(prefix)
            return [f for f in files if f.endswith('.json')]
        else:
            container = self.storage.get_container_client(self.container_name)
            blobs = container.list_blobs(name_starts_with=prefix)
            return [blob.name for blob in blobs if blob.name.endswith('.json')]
    
    def get_cache_status(self) -> Dict[str, Any]:
        prefix = 'cache/yle/articles/'
        articles = self.list_articles(prefix)
        
        return {
            "articles_prefix": prefix,
            "articles_count": len(articles),
            "article_paths": articles[:10]
        }
