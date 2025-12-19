import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from .storage_factory import get_table_storage

logger = logging.getLogger(__name__)


def get_client_ip(request) -> str:
    x_forwarded_for = request.headers.get('X-Forwarded-For', '')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    
    x_real_ip = request.headers.get('X-Real-Ip', '')
    if x_real_ip:
        return x_real_ip
    
    client_ip = request.headers.get('X-Client-Ip', '')
    if client_ip:
        return client_ip
    
    return 'unknown'


class IPRateLimiter:
    def __init__(self, table_name: str, window_minutes: int = 15):
        self.table_name = table_name
        self.table_client = get_table_storage(table_name)
        self.window_minutes = window_minutes
        logger.info(f"Initialized IPRateLimiter with table {table_name}, window={window_minutes}min")
    
    def _get_time_window_key(self) -> str:
        now = datetime.now(timezone.utc)
        window_start = now.replace(minute=(now.minute // self.window_minutes) * self.window_minutes, second=0, microsecond=0)
        return window_start.strftime("%Y-%m-%dT%H:%M")
    
    def _get_row_key(self, ip_address: str) -> str:
        window_key = self._get_time_window_key()
        return f"{ip_address}_{window_key}"
    
    def check_limit(self, ip_address: str, limit: int) -> bool:
        row_key = self._get_row_key(ip_address)
        
        try:
            entity = self.table_client.get_entity(
                partition_key="auth_rate_limits",
                row_key=row_key
            )
            request_count = entity.get('request_count', 0)
            
            if request_count >= limit:
                logger.warning(f"Rate limit exceeded for IP {ip_address}: {request_count}/{limit}")
                return False
            
            return True
        except Exception:
            return True
    
    def get_count(self, ip_address: str) -> int:
        row_key = self._get_row_key(ip_address)
        
        try:
            entity = self.table_client.get_entity(
                partition_key="auth_rate_limits",
                row_key=row_key
            )
            return entity.get('request_count', 0)
        except Exception:
            return 0
    
    def increment(self, ip_address: str):
        row_key = self._get_row_key(ip_address)
        window_key = self._get_time_window_key()
        
        try:
            try:
                entity = self.table_client.get_entity(
                    partition_key="auth_rate_limits",
                    row_key=row_key
                )
                request_count = entity.get('request_count', 0) + 1
            except Exception:
                request_count = 1
            
            entity = {
                'PartitionKey': 'auth_rate_limits',
                'RowKey': row_key,
                'ip_address': ip_address,
                'window': window_key,
                'request_count': request_count,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            if hasattr(self.table_client, 'upsert_entity'):
                self.table_client.upsert_entity(entity)
            else:
                self.table_client.create_entity(entity)
            
            logger.debug(f"Incremented rate limit for IP {ip_address}: {request_count}")
        except Exception as e:
            logger.error(f"Error incrementing rate limit: {e}")


class DailyRateLimiter:
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.table_client = get_table_storage(table_name)
        logger.info(f"Initialized DailyRateLimiter with table {table_name}")
    
    def _get_date_key(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    def _get_row_key(self, function_name: str) -> str:
        date_key = self._get_date_key()
        return f"{function_name}_{date_key}"
    
    def check_limit(self, function_name: str, daily_limit: int) -> bool:
        row_key = self._get_row_key(function_name)
        
        try:
            if hasattr(self.table_client, 'get_entity'):
                entity = self.table_client.get_entity(
                    partition_key="rate_limits",
                    row_key=row_key
                )
                request_count = entity.get('request_count', 0)
            else:
                entity = self.table_client.get_entity(
                    partition_key="rate_limits",
                    row_key=row_key
                )
                request_count = entity.get('request_count', 0)
            
            if request_count >= daily_limit:
                logger.warning(f"Rate limit exceeded for {function_name}: {request_count}/{daily_limit}")
                return False
            
            return True
        except Exception as e:
            logger.debug(f"No existing rate limit entry for {function_name}: {e}")
            return True
    
    def get_daily_count(self, function_name: str) -> int:
        row_key = self._get_row_key(function_name)
        
        try:
            if hasattr(self.table_client, 'get_entity'):
                entity = self.table_client.get_entity(
                    partition_key="rate_limits",
                    row_key=row_key
                )
                return entity.get('request_count', 0)
            else:
                entity = self.table_client.get_entity(
                    partition_key="rate_limits",
                    row_key=row_key
                )
                return entity.get('request_count', 0)
        except Exception:
            return 0
    
    def increment(self, function_name: str):
        row_key = self._get_row_key(function_name)
        date_key = self._get_date_key()
        
        try:
            if hasattr(self.table_client, 'get_entity'):
                try:
                    entity = self.table_client.get_entity(
                        partition_key="rate_limits",
                        row_key=row_key
                    )
                    request_count = entity.get('request_count', 0) + 1
                except Exception:
                    request_count = 1
                
                entity = {
                    'PartitionKey': 'rate_limits',
                    'RowKey': row_key,
                    'function_name': function_name,
                    'date': date_key,
                    'request_count': request_count,
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
                
                if hasattr(self.table_client, 'upsert_entity'):
                    self.table_client.upsert_entity(entity)
                else:
                    self.table_client.create_entity(entity)
            else:
                try:
                    entity = self.table_client.get_entity(
                        partition_key="rate_limits",
                        row_key=row_key
                    )
                    request_count = entity.get('request_count', 0) + 1
                except Exception:
                    request_count = 1
                
                entity = {
                    'PartitionKey': 'rate_limits',
                    'RowKey': row_key,
                    'function_name': function_name,
                    'date': date_key,
                    'request_count': request_count,
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
                
                self.table_client.upsert_entity(entity)
            
            logger.debug(f"Incremented rate limit for {function_name}: {request_count}")
        except Exception as e:
            logger.error(f"Error incrementing rate limit: {e}")
            raise
