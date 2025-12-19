import os
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from .storage_factory import get_blob_storage

logger = logging.getLogger(__name__)


class CacheCleaner:
    def __init__(self, container_name: str = None):
        self.storage = get_blob_storage()
        self.container_name = container_name or os.getenv('STORAGE_CONTAINER', 'finnish-news-tools')
        self.use_local = os.getenv('USE_LOCAL_STORAGE', 'false').lower() == 'true'
    
    def cleanup_expired(self, cache_path: str, ttl_hours: int = 1) -> int:
        logger.info(f"Cleaning up expired cache entries in {cache_path} (TTL: {ttl_hours}h)")
        cleaned_count = 0
        
        if self.use_local:
            files = self.storage.list_files(cache_path)
            for blob_path in files:
                try:
                    cache_data = self.storage.read_file(blob_path)
                    if cache_data and isinstance(cache_data, dict):
                        if 'expires_at' in cache_data:
                            expires_at = datetime.fromisoformat(cache_data['expires_at'].replace('Z', '+00:00'))
                            if expires_at < datetime.now(timezone.utc):
                                self.storage.delete_file(blob_path)
                                cleaned_count += 1
                                logger.debug(f"Deleted expired cache: {blob_path}")
                        else:
                            if 'fetch_timestamp' in cache_data.get('feed_metadata', {}):
                                fetch_time = datetime.fromisoformat(
                                    cache_data['feed_metadata']['fetch_timestamp'].replace('Z', '+00:00')
                                )
                            elif 'scraped_at' in cache_data:
                                fetch_time = datetime.fromisoformat(cache_data['scraped_at'].replace('Z', '+00:00'))
                            else:
                                continue
                            
                            if fetch_time + timedelta(hours=ttl_hours) < datetime.now(timezone.utc):
                                self.storage.delete_file(blob_path)
                                cleaned_count += 1
                                logger.debug(f"Deleted expired cache (by timestamp): {blob_path}")
                except Exception as e:
                    logger.warning(f"Error checking cache expiration for {blob_path}: {e}")
        else:
            container = self.storage.get_container_client(self.container_name)
            blobs = container.list_blobs(name_starts_with=cache_path)
            
            for blob in blobs:
                try:
                    blob_client = container.get_blob_client(blob.name)
                    import json
                    blob_data = blob_client.download_blob().readall()
                    cache_data = json.loads(blob_data.decode('utf-8'))
                    
                    if 'expires_at' in cache_data:
                        expires_at = datetime.fromisoformat(cache_data['expires_at'].replace('Z', '+00:00'))
                        if expires_at < datetime.now(timezone.utc):
                            blob_client.delete_blob()
                            cleaned_count += 1
                            logger.debug(f"Deleted expired cache: {blob.name}")
                    else:
                        if 'fetch_timestamp' in cache_data.get('feed_metadata', {}):
                            fetch_time = datetime.fromisoformat(
                                cache_data['feed_metadata']['fetch_timestamp'].replace('Z', '+00:00')
                            )
                        elif 'scraped_at' in cache_data:
                            fetch_time = datetime.fromisoformat(cache_data['scraped_at'].replace('Z', '+00:00'))
                        else:
                            continue
                        
                        if fetch_time + timedelta(hours=ttl_hours) < datetime.now(timezone.utc):
                            blob_client.delete_blob()
                            cleaned_count += 1
                            logger.debug(f"Deleted expired cache (by timestamp): {blob.name}")
                except Exception as e:
                    logger.warning(f"Error checking cache expiration for {blob.name}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired cache entries")
        return cleaned_count
    
    def check_cache_valid(self, blob_path: str, ttl_hours: int = 1) -> bool:
        if self.use_local:
            if not self.storage.file_exists(blob_path):
                return False
            
            cache_data = self.storage.read_file(blob_path)
            if not cache_data or not isinstance(cache_data, dict):
                return False
            
            if 'expires_at' in cache_data:
                expires_at = datetime.fromisoformat(cache_data['expires_at'].replace('Z', '+00:00'))
                return expires_at > datetime.now(timezone.utc)
            else:
                if 'fetch_timestamp' in cache_data.get('feed_metadata', {}):
                    fetch_time = datetime.fromisoformat(
                        cache_data['feed_metadata']['fetch_timestamp'].replace('Z', '+00:00')
                    )
                elif 'scraped_at' in cache_data:
                    fetch_time = datetime.fromisoformat(cache_data['scraped_at'].replace('Z', '+00:00'))
                else:
                    return False
                
                return fetch_time + timedelta(hours=ttl_hours) > datetime.now(timezone.utc)
        else:
            container = self.storage.get_container_client(self.container_name)
            blob_client = container.get_blob_client(blob_path)
            
            try:
                import json
                blob_data = blob_client.download_blob().readall()
                cache_data = json.loads(blob_data.decode('utf-8'))
                
                if 'expires_at' in cache_data:
                    expires_at = datetime.fromisoformat(cache_data['expires_at'].replace('Z', '+00:00'))
                    return expires_at > datetime.now(timezone.utc)
                else:
                    if 'fetch_timestamp' in cache_data.get('feed_metadata', {}):
                        fetch_time = datetime.fromisoformat(
                            cache_data['feed_metadata']['fetch_timestamp'].replace('Z', '+00:00')
                        )
                    elif 'scraped_at' in cache_data:
                        fetch_time = datetime.fromisoformat(cache_data['scraped_at'].replace('Z', '+00:00'))
                    else:
                        return False
                    
                    return fetch_time + timedelta(hours=ttl_hours) > datetime.now(timezone.utc)
            except Exception:
                return False
