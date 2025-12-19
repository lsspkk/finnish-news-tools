import azure.functions as func
import os
from typing import Optional


def get_cors_origin() -> Optional[str]:
    """Get the allowed CORS origin from environment or request headers."""
    # In production, Azure Functions CORS is configured at app level
    # But we can also check for specific origins if needed
    return os.getenv('CORS_ALLOWED_ORIGIN')


def add_cors_headers(response: func.HttpResponse, request: func.HttpRequest) -> func.HttpResponse:
    """Add CORS headers to the response based on the request origin."""
    origin = request.headers.get('Origin')
    
    # If no origin header, don't add CORS headers
    if not origin:
        return response
    
    # Get allowed origins from environment or use the request origin
    # Azure Functions CORS configuration handles this at app level,
    # but we add headers here for explicit control
    allowed_origin = get_cors_origin() or origin
    
    # Add CORS headers
    response.headers['Access-Control-Allow-Origin'] = allowed_origin
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, HEAD'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Token, X-Username, X-Issued-Date, Authorization'
    response.headers['Access-Control-Allow-Credentials'] = 'false'
    
    return response


def create_cors_response(
    body: str,
    status_code: int,
    mimetype: str = "application/json",
    request: Optional[func.HttpRequest] = None
) -> func.HttpResponse:
    """Create an HttpResponse with CORS headers."""
    response = func.HttpResponse(
        body=body,
        status_code=status_code,
        mimetype=mimetype
    )
    
    if request:
        response = add_cors_headers(response, request)
    
    return response

