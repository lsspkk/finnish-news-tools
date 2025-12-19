import os
import json
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
try:
    from ..shared.storage_factory import get_blob_storage
except ImportError:
    from shared.storage_factory import get_blob_storage

logger = logging.getLogger(__name__)


def hash_paragraphs(paragraphs: List[str]) -> str:
    content = '\n'.join(paragraphs)
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


class TranslationCacheManager:
    def __init__(self, cache_ttl_hours: int = 24):
        self.storage = get_blob_storage()
        self.container_name = os.getenv('STORAGE_CONTAINER', 'finnish-news-tools')
        self.cache_ttl_hours = cache_ttl_hours
        self.use_local = os.getenv('USE_LOCAL_STORAGE', 'false').lower() == 'true'
        self.cache_prefix = 'cache/translations/'
        logger.info(f"Initialized TranslationCacheManager with TTL: {cache_ttl_hours}h")
    
    def _get_cache_key(self, article_id: str, source_lang: str, target_lang: str) -> str:
        return f"{article_id}/{source_lang}_{target_lang}"
    
    def _get_blob_path(self, cache_key: str) -> str:
        return f"{self.cache_prefix}{cache_key}.json"
    
    def get(self, article_id: str, source_lang: str, target_lang: str, paragraphs: List[str]) -> Optional[Dict[str, Any]]:
        cache_key = self._get_cache_key(article_id, source_lang, target_lang)
        blob_path = self._get_blob_path(cache_key)
        paragraph_hash = hash_paragraphs(paragraphs)
        
        if self.use_local:
            if not self.storage.file_exists(blob_path):
                return None
            
            cache_data = self.storage.read_file(blob_path)
            if not cache_data or not isinstance(cache_data, dict):
                return None
            
            if 'expires_at' in cache_data:
                expires_at = datetime.fromisoformat(cache_data['expires_at'].replace('Z', '+00:00'))
                if expires_at < datetime.now(timezone.utc):
                    logger.debug(f"Cache expired for {blob_path}")
                    return None
            
            cached_hash = cache_data.get('paragraph_hash')
            if cached_hash != paragraph_hash:
                logger.debug(f"Paragraph hash mismatch for {blob_path}")
                return None
            
            logger.info(f"Cache hit for {blob_path}")
            return cache_data
        else:
            container = self.storage.get_container_client(self.container_name)
            blob_client = container.get_blob_client(blob_path)
            
            try:
                blob_data = blob_client.download_blob().readall()
                cache_data = json.loads(blob_data.decode('utf-8'))
                
                if 'expires_at' in cache_data:
                    expires_at = datetime.fromisoformat(cache_data['expires_at'].replace('Z', '+00:00'))
                    if expires_at < datetime.now(timezone.utc):
                        logger.debug(f"Cache expired for {blob_path}")
                        return None
                
                cached_hash = cache_data.get('paragraph_hash')
                if cached_hash != paragraph_hash:
                    logger.debug(f"Paragraph hash mismatch for {blob_path}")
                    return None
                
                logger.info(f"Cache hit for {blob_path}")
                return cache_data
            except Exception as e:
                logger.debug(f"Cache miss for {blob_path}: {e}")
                return None
    
    def save(self, article_id: str, source_lang: str, target_lang: str, 
             paragraphs: List[str], translations: List[str]) -> str:
        cache_key = self._get_cache_key(article_id, source_lang, target_lang)
        blob_path = self._get_blob_path(cache_key)
        paragraph_hash = hash_paragraphs(paragraphs)
        
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=self.cache_ttl_hours)
        
        cache_data = {
            'article_id': article_id,
            'source_lang': source_lang,
            'target_lang': target_lang,
            'paragraphs': paragraphs,
            'translations': translations,
            'paragraph_hash': paragraph_hash,
            'created_at': now.isoformat(),
            'expires_at': expires_at.isoformat(),
            'cache_ttl_hours': self.cache_ttl_hours
        }
        
        if self.use_local:
            self.storage.save_file(blob_path, cache_data)
        else:
            container = self.storage.get_container_client(self.container_name)
            blob_client = container.get_blob_client(blob_path)
            blob_client.upload_blob(
                json.dumps(cache_data, indent=2, ensure_ascii=False),
                overwrite=True,
                encoding='utf-8'
            )
        
        logger.info(f"Saved translation cache to {blob_path}")
        return blob_path
    
    def cleanup_expired(self) -> int:
        logger.info(f"Cleaning up expired translation cache entries")
        cleaned_count = 0
        
        if self.use_local:
            files = self.storage.list_files(self.cache_prefix)
            for blob_path in files:
                if not blob_path.endswith('.json'):
                    continue
                
                try:
                    cache_data = self.storage.read_file(blob_path)
                    if cache_data and isinstance(cache_data, dict):
                        if 'expires_at' in cache_data:
                            expires_at = datetime.fromisoformat(cache_data['expires_at'].replace('Z', '+00:00'))
                            if expires_at < datetime.now(timezone.utc):
                                self.storage.delete_file(blob_path)
                                cleaned_count += 1
                                logger.debug(f"Deleted expired cache: {blob_path}")
                except Exception as e:
                    logger.warning(f"Error checking cache expiration for {blob_path}: {e}")
        else:
            container = self.storage.get_container_client(self.container_name)
            blobs = container.list_blobs(name_starts_with=self.cache_prefix)
            
            for blob in blobs:
                if not blob.name.endswith('.json'):
                    continue
                
                try:
                    blob_client = container.get_blob_client(blob.name)
                    blob_data = blob_client.download_blob().readall()
                    cache_data = json.loads(blob_data.decode('utf-8'))
                    
                    if 'expires_at' in cache_data:
                        expires_at = datetime.fromisoformat(cache_data['expires_at'].replace('Z', '+00:00'))
                        if expires_at < datetime.now(timezone.utc):
                            blob_client.delete_blob()
                            cleaned_count += 1
                            logger.debug(f"Deleted expired cache: {blob.name}")
                except Exception as e:
                    logger.warning(f"Error checking cache expiration for {blob.name}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired translation cache entries")
        return cleaned_count
