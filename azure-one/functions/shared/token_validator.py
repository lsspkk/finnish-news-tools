import os
import hmac
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def get_auth_secret() -> str:
    secret = os.getenv('AUTH_SECRET')
    if not secret:
        raise ValueError("AUTH_SECRET environment variable not set")
    return secret


def generate_token(username: str, issued_date: str) -> str:
    secret = get_auth_secret()
    message = f"{username}:{issued_date}"
    token = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return token


def validate_token(token: str, username: str, issued_date: str) -> bool:
    try:
        issued_dt = datetime.fromisoformat(issued_date.replace('Z', '+00:00'))
        now = datetime.now(issued_dt.tzinfo)
        
        if now - issued_dt > timedelta(days=30):
            logger.warning(f"Token expired for user {username}")
            return False
        
        expected_token = generate_token(username, issued_date)
        is_valid = hmac.compare_digest(token, expected_token)
        
        if not is_valid:
            logger.warning(f"Invalid token for user {username}")
        
        return is_valid
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return False


def extract_auth_headers(request) -> Optional[Tuple[str, str, str]]:
    token = request.headers.get('X-Token') or request.headers.get('Authorization', '').replace('Bearer ', '')
    issued_date = request.headers.get('X-Issued-Date')
    username = request.headers.get('X-Username')
    
    if not token or not issued_date or not username:
        return None
    
    return (token, username, issued_date)


def validate_request(request) -> Tuple[bool, Optional[str]]:
    auth_data = extract_auth_headers(request)
    
    if not auth_data:
        return (False, "Missing authentication headers")
    
    token, username, issued_date = auth_data
    
    if not validate_token(token, username, issued_date):
        return (False, "Invalid or expired token")
    
    return (True, username)
