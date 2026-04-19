# CORS Configuration for MemeGPT API

## Overview

This document describes the Cross-Origin Resource Sharing (CORS) configuration for the MemeGPT FastAPI backend. CORS is essential for enabling secure communication between the Next.js frontend and the FastAPI backend when they run on different ports or domains.

## Configuration Files

### 1. Core Configuration (`backend/core/config.py`)

The CORS settings are defined in the `Settings` class:

```python
# CORS Configuration
cors_origins: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
cors_allow_credentials: bool = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
cors_allow_methods: List[str] = os.getenv("CORS_ALLOW_METHODS", "GET,POST,PUT,PATCH,DELETE,OPTIONS").split(",")
cors_allow_headers: List[str] = os.getenv("CORS_ALLOW_HEADERS", "Authorization,Content-Type,X-API-Key,X-Requested-With,Accept,Origin,User-Agent").split(",")
cors_max_age: int = int(os.getenv("CORS_MAX_AGE", "600"))
```

### 2. CORS Middleware (`backend/core/cors.py`)

The dedicated CORS module provides:
- Secure origin validation
- Environment-specific configuration
- Security headers middleware
- Production safety checks

### 3. Main Application (`backend/main.py`)

CORS middleware is configured in the FastAPI application:

```python
from .core.cors import setup_cors_middleware
setup_cors_middleware(app)
```

## Environment Variables

Configure CORS through environment variables in `.env`:

```bash
# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,PATCH,DELETE,OPTIONS
CORS_ALLOW_HEADERS=Authorization,Content-Type,X-API-Key,X-Requested-With,Accept,Origin,User-Agent
CORS_MAX_AGE=600
ENVIRONMENT=development
```

## Security Features

### 1. Origin Validation

- **Development**: Allows localhost variations for development
- **Production**: Strict origin validation, no wildcards allowed
- **Automatic**: Removes duplicates and normalizes URLs

### 2. Security Headers

The `SecurityHeadersMiddleware` adds essential security headers:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: (production only)
```

### 3. Exposed Headers

Rate limiting and pagination headers are exposed for frontend use:

```
X-RateLimit-Limit
X-RateLimit-Remaining
X-RateLimit-Reset
X-Total-Count
X-Page-Count
X-Request-ID
```

## Development vs Production

### Development Configuration

```bash
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CORS_ALLOW_CREDENTIALS=true
```

- Allows localhost variations
- Relaxed security for development
- Additional debugging headers

### Production Configuration

```bash
ENVIRONMENT=production
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CORS_ALLOW_CREDENTIALS=true
```

- Strict origin validation
- No wildcard origins allowed
- Additional security headers (CSP)
- HTTPS enforcement warnings

## API Endpoints and CORS

All API endpoints support CORS with the configured settings:

### Meme Generation
- `POST /api/memes/generate` - Generate memes (requires auth headers)
- `GET /api/memes/public` - Public meme gallery
- `GET /api/memes/my` - User's memes (requires auth)

### Authentication
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Current user info

### Billing
- `POST /api/stripe/checkout` - Create checkout session
- `POST /api/stripe/portal` - Billing portal

## Frontend Integration

The frontend API client (`lib/api.ts`) is configured to work with CORS:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Headers automatically include:
// - Content-Type: application/json
// - Authorization: Bearer <token>
// - Origin: (automatically set by browser)
```

## Troubleshooting

### Common CORS Issues

1. **Origin not allowed**
   - Check `CORS_ORIGINS` environment variable
   - Ensure frontend URL matches exactly
   - No trailing slashes in origins

2. **Credentials not working**
   - Set `CORS_ALLOW_CREDENTIALS=true`
   - Ensure frontend sends credentials
   - Check cookie settings

3. **Headers blocked**
   - Add required headers to `CORS_ALLOW_HEADERS`
   - Check for custom headers in requests

4. **Methods not allowed**
   - Add HTTP methods to `CORS_ALLOW_METHODS`
   - Ensure OPTIONS method is included

### Debugging CORS

1. Check browser developer tools Network tab
2. Look for preflight OPTIONS requests
3. Verify response headers match configuration
4. Check server logs for CORS validation messages

### Testing CORS

Use the provided test script:

```bash
python backend/test_cors_config.py
```

Or test manually with curl:

```bash
# Test preflight request
curl -X OPTIONS \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  http://localhost:8000/api/memes/public

# Test simple request
curl -X GET \
  -H "Origin: http://localhost:3000" \
  http://localhost:8000/health
```

## Security Best Practices

1. **Never use wildcard origins in production**
2. **Minimize allowed headers and methods**
3. **Use HTTPS in production**
4. **Regularly audit CORS configuration**
5. **Monitor for unauthorized origins**
6. **Keep max-age reasonable (600-3600 seconds)**

## Migration Notes

This CORS configuration supports the MemeGPT v2 migration by:

1. **Enabling frontend-backend communication** across different ports
2. **Supporting authentication flows** with credential handling
3. **Allowing API access** with proper header support
4. **Providing security** with production-ready configuration
5. **Supporting development** with localhost variations

The configuration is designed to be secure by default while providing flexibility for development and production environments.