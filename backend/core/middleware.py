from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
import logging
from typing import Optional

from ..services.rate_limit import rate_limit_request
from ..services.auth import verify_token
from ..core.config import settings

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
        # Only rate limit meme generation and jobs creation
        rate_limited_paths = ["/api/memes/generate", "/api/jobs"]
        
        should_rate_limit = any(request.url.path.startswith(path) for path in rate_limited_paths)
        
        if should_rate_limit and request.method == "POST":
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
                _, remaining = await rate_limit_request(request, user_id=user_id)
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
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self' https:; "
            "media-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Disable caching for sensitive responses
        if request.method == "POST" or "/auth/" in request.url.path:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response