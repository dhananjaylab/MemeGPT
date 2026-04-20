"""
CORS (Cross-Origin Resource Sharing) configuration for MemeGPT API.

This module provides secure CORS configuration for frontend communication
with proper security considerations for both development and production environments.
"""

import logging
from typing import List, Optional
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY" if settings.is_production else "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Add CSP header - Allow CDN for Swagger UI docs
        # Don't apply strict CSP to docs/redoc endpoints
        if not request.url.path.startswith("/docs") and not request.url.path.startswith("/redoc"):
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https:; "
                "font-src 'self' data: https://cdn.jsdelivr.net; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none';"
            )
            response.headers["Content-Security-Policy"] = csp_policy
        
        return response


def get_cors_origins() -> List[str]:
    """
    Get allowed CORS origins based on environment configuration.
    
    Returns:
        List of allowed origin URLs
    """
    origins = []
    
    # Always include configured frontend URL
    if settings.frontend_url:
        origins.append(settings.frontend_url.rstrip('/'))
    
    # Add configured CORS origins
    for origin in settings.cors_origins:
        if origin and origin.strip():
            origins.append(origin.strip().rstrip('/'))
    
    # In development, allow common localhost variations
    if not settings.is_production:
        dev_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",  # Alternative dev port
            "http://127.0.0.1:3001",
            "http://0.0.0.0:3000",   # Docker development
            "http://0.0.0.0:3001",
        ]
        for origin in dev_origins:
            if origin not in origins:
                origins.append(origin)
    
    # Remove duplicates and empty strings
    unique_origins = list(filter(None, set(origins)))
    
    # Log configuration for debugging
    logger.info(f"CORS Origins configured: {unique_origins}")
    
    return unique_origins


def validate_cors_config() -> None:
    """Validate CORS configuration for security"""
    
    origins = get_cors_origins()
    
    # Security checks
    if settings.is_production:
        # Check for wildcard origins in production
        if "*" in origins:
            logger.error("Wildcard CORS origin (*) detected in production - this is a security risk!")
            raise ValueError("Wildcard CORS origins not allowed in production")
        
        # Check for localhost origins in production
        localhost_origins = [o for o in origins if "localhost" in o or "127.0.0.1" in o]
        if localhost_origins:
            logger.warning(f"Localhost origins detected in production: {localhost_origins}")
        
        # Ensure HTTPS origins in production
        http_origins = [o for o in origins if o.startswith("http://")]
        if http_origins:
            logger.warning(f"HTTP origins detected in production (consider HTTPS): {http_origins}")
    
    # Check for empty origins
    if not origins:
        logger.warning("No CORS origins configured - API may not be accessible from frontend")


def setup_cors_middleware(app: FastAPI) -> None:
    """
    Configure CORS middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    
    # Validate configuration
    validate_cors_config()
    
    # Get allowed origins
    allowed_origins = get_cors_origins()
    
    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
        max_age=settings.cors_max_age,
        expose_headers=[
            # Rate limiting headers
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining", 
            "X-RateLimit-Reset",
            "X-RateLimit-Window",
            # Pagination headers
            "X-Total-Count",
            "X-Page-Count",
            "X-Page-Size",
            # API response headers
            "X-Request-ID",
            "X-Response-Time",
        ]
    )
    
    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Log final configuration
    logger.info("CORS middleware configured successfully")
    logger.info(f"Allowed origins: {allowed_origins}")
    logger.info(f"Allow credentials: {settings.cors_allow_credentials}")
    logger.info(f"Allowed methods: {settings.cors_allow_methods}")
    logger.info(f"Allowed headers: {settings.cors_allow_headers}")
    logger.info(f"Max age: {settings.cors_max_age} seconds")


def get_cors_preflight_response(origin: Optional[str] = None) -> Response:
    """
    Create a manual CORS preflight response for complex scenarios.
    
    Args:
        origin: The requesting origin
        
    Returns:
        Response with appropriate CORS headers
    """
    
    allowed_origins = get_cors_origins()
    
    # Check if origin is allowed
    if origin and origin in allowed_origins:
        response = Response(status_code=200)
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = ",".join(settings.cors_allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ",".join(settings.cors_allow_headers)
        response.headers["Access-Control-Max-Age"] = str(settings.cors_max_age)
        
        if settings.cors_allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response
    
    # Return 403 for disallowed origins
    return Response(status_code=403, content="Origin not allowed")


# CORS configuration constants for reference
CORS_SECURITY_BEST_PRACTICES = {
    "production": {
        "allow_origins": "Specific domains only, never '*'",
        "allow_credentials": "Only if necessary for authentication",
        "allow_methods": "Only required HTTP methods",
        "allow_headers": "Minimal required headers",
        "max_age": "Reasonable cache time (600-3600 seconds)",
    },
    "development": {
        "allow_origins": "Localhost variations for development",
        "allow_credentials": "True for session-based auth",
        "allow_methods": "All required methods for development",
        "allow_headers": "Development and debugging headers",
        "max_age": "Short cache time for rapid iteration",
    }
}