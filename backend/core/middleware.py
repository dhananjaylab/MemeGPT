from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
import logging
from typing import Optional

from services.rate_limit import rate_limit_request
from services.auth import verify_token
from core.config import settings

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.url}")
        
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(f"Response: {response.status_code} - {process_time:.4f}s")
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to apply rate limiting to specific API routes.
    """
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        should_rate_limit = False
        custom_limit = None

        # Enforce generation daily limits (plan-based by default).
        if method == "POST" and path.startswith("/api/memes/generate"):
            should_rate_limit = True

        # Apply generous read limits for new high-read endpoints.
        if method == "GET" and path.startswith("/api/memes/templates"):
            should_rate_limit = True
            custom_limit = settings.rate_limit_templates_read

        if method == "GET" and path.startswith("/api/trending/topics"):
            should_rate_limit = True
            custom_limit = settings.rate_limit_trending_read

        if should_rate_limit:
            user_id = None
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                payload = verify_token(token)
                if payload:
                    user_id = payload.get("sub")
            
            # API Key check
            api_key = request.headers.get("X-API-Key")
            
            try:
                # We call rate_limit_request which will handle either User ID or IP
                _, remaining = await rate_limit_request(
                    request,
                    user_id=user_id,
                    custom_limit=custom_limit,
                )
                # Store in state so routers can access it (e.g. for returning remaining count in API)
                request.state.rate_limit_remaining = remaining
            except HTTPException as e:
                return JSONResponse(
                    status_code=e.status_code,
                    content={"detail": e.detail},
                    headers=e.headers
                )
        
        return await call_next(request)


def register_middleware(app: FastAPI):
    """Register all middleware for the FastAPI app"""
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    Protects against common web vulnerabilities.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Clickjacking protection
        response.headers["X-Frame-Options"] = "DENY" if settings.is_production else "SAMEORIGIN"
        
        # HTTPS security
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Content Security Policy - Allow CDN for Swagger UI
        # Don't apply strict CSP to docs endpoints
        if not request.url.path.startswith("/docs") and not request.url.path.startswith("/redoc"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https:; "
                "font-src 'self' data: https://cdn.jsdelivr.net; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none';"
            )
        
        return response