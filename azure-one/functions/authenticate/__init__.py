# Authenticator for local testing purposes
# Uses simple password validation
# For production, use authenticate/__init__.py.local with secure validation

import azure.functions as func
import json
import os
import logging
from datetime import datetime, timezone, timedelta
try:
    from ..shared.app import app
    from ..shared.token_validator import generate_token
    from ..shared.rate_limiter import IPRateLimiter, get_client_ip
except ImportError:
    from shared.app import app
    from shared.token_validator import generate_token
    from shared.rate_limiter import IPRateLimiter, get_client_ip

logger = logging.getLogger(__name__)


def validate_password(password: str) -> bool:
    return password == "Hello world!"


@app.route(route="authenticate", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def authenticate(req: func.HttpRequest) -> func.HttpResponse:
    logger.info('Authenticate function triggered')
    
    try:
        client_ip = get_client_ip(req)
        rate_limiter = IPRateLimiter(
            table_name=os.getenv('RATE_LIMIT_TABLE_NAME', 'rateLimits'),
            window_minutes=int(os.getenv('AUTH_RATE_LIMIT_WINDOW_MINUTES', '15'))
        )
        rate_limit = int(os.getenv('AUTH_RATE_LIMIT_PER_WINDOW', '5'))
        
        if not rate_limiter.check_limit(client_ip, rate_limit):
            current_count = rate_limiter.get_count(client_ip)
            logger.warning(f"Rate limit exceeded for IP {client_ip}: {current_count}/{rate_limit}")
            return func.HttpResponse(
                json.dumps({
                    "error": "Too many authentication attempts. Please try again later.",
                    "retry_after_minutes": rate_limiter.window_minutes
                }),
                status_code=429,
                mimetype="application/json"
            )
        
        body = req.get_json()
        username = body.get('username', '')
        password = body.get('password', '')
        
        if not username or not password:
            rate_limiter.increment(client_ip)
            return func.HttpResponse(
                json.dumps({"error": "Username and password required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        rate_limiter.increment(client_ip)
        
        if not validate_password(password):
            logger.warning(f"Authentication failed for user {username} from IP {client_ip}")
            return func.HttpResponse(
                json.dumps({"error": "Invalid credentials"}),
                status_code=401,
                mimetype="application/json"
            )
        
        now = datetime.now(timezone.utc)
        issued_date = now.isoformat()
        token = generate_token(username, issued_date)
        
        # expires_at is example value showing recommended refresh time
        # Actual token validation allows 30 days from issued_date
        expires_at = (now + timedelta(days=7)).isoformat()
        
        logger.info(f"Authentication successful for user {username}")
        
        return func.HttpResponse(
            json.dumps({
                "success": True,
                "token": token,
                "username": username,
                "issued_at": issued_date,
                "expires_at": expires_at
            }),
            status_code=200,
            mimetype="application/json"
        )
    
    except Exception as e:
        logger.error(f"Error in authenticate function: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
