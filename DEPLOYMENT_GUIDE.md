# MemeGPT Deployment & Configuration Guide

## Overview

This document provides comprehensive information about the production-ready deployment configuration, storage optimization, and security setup for MemeGPT.

## Table of Contents

- [Storage Configuration (3.3)](#storage-configuration-33)
- [Environment Configuration (4.1)](#environment-configuration-41)
- [Docker & Deployment (4.2)](#docker--deployment-42)
- [Security Configuration (4.3)](#security-configuration-43)
- [Deployment Instructions](#deployment-instructions)
- [Monitoring & Logging](#monitoring--logging)

---

## Storage Configuration (3.3)

### 3.3.1 Configure Cloudflare R2 Bucket and Permissions

**Files:**
- `backend/services/r2_config.py` - Enhanced with CDN caching policies
- `backend/services/r2_monitoring.py` - New backup and monitoring service

**Implementation:**
- R2ConfigManager handles bucket creation and permissions
- Automatic CORS configuration for cross-origin requests
- Lifecycle policies for automatic cleanup:
  - Temp files: deleted after 7 days
  - Failed uploads: deleted after 1 day
  - Old versions: deleted after 30 days

**Usage:**
```python
from backend.services.r2_config import R2ConfigManager

manager = R2ConfigManager()
manager.setup_bucket()  # Complete setup
```

### 3.3.2 Setup CDN Caching Policies for Images

**Implementation:**
```python
from backend.services.r2_config import CDNCachingPolicy

# Get cache control header for any object
cache_header = CDNCachingPolicy.get_cache_control_header("memes/image.jpg")
# Returns: "public, max-age=31536000, immutable"  (1 year cache)

# Cache rules by prefix:
# - memes/: 1 year (immutable - for hash-named files)
# - templates/: 30 days
# - uploads/: 7 days
# - api/: no-cache
```

**Cache Strategy:**
- Meme images: Aggressive caching (1 year) with immutable flag
- Templates: Medium-term caching (30 days)
- User uploads: Standard caching (7 days)
- API responses: No caching

### 3.3.3 Implement Image Optimization Pipeline

**Files:**
- `backend/services/image_optimizer.py` - New image optimization service

**Features:**
- Multiple image formats: JPEG, PNG, WebP, AVIF
- Responsive image generation (thumbnail, small, medium, large, original)
- Quality presets: high (90), medium (75), low (60)
- Automatic format conversion based on source
- Optimization statistics (compression ratio, size reduction)

**Usage:**
```python
from backend.services.image_optimizer import AsyncImageOptimizer
from services.image_optimizer import ImageFormat

optimizer = AsyncImageOptimizer()

# Single optimization
optimized = await optimizer.optimize_image_async(
    image_data,
    target_size="medium",
    quality="medium",
    target_format=ImageFormat.WEBP
)

# Generate responsive images
responsive = await optimizer.generate_responsive_images_async(
    image_data,
    quality="medium",
    include_formats=[ImageFormat.JPEG, ImageFormat.WEBP]
)
# Output: {
#   'thumbnail_jpeg': bytes,
#   'thumbnail_webp': bytes,
#   'small_jpeg': bytes,
#   ...
# }
```

### 3.3.4 Create Backup Strategy for R2 Storage

**Files:**
- `backend/services/r2_monitoring.py` - Backup management

**Backup Features:**
- Automatic bucket versioning
- Point-in-time snapshots with metadata manifests
- Selective object backup
- Restore capabilities with optional prefix
- Automatic cleanup of old backups (configurable retention)

**Usage:**
```python
from backend.services.r2_monitoring import R2BackupManager

backup_manager = R2BackupManager()

# Enable versioning
backup_manager.backup_bucket_versioning(enable=True)

# Create full snapshot
metadata = backup_manager.backup_bucket_snapshot()

# Restore from backup
backup_manager.restore_from_backup(backup_id="20240101_120000")

# Cleanup old backups (keep last 30 days)
deleted_count = backup_manager.cleanup_old_backups(retention_days=30)
```

**Backup Schedule (from environment):**
- Daily automatic backups at configured time
- Retention: 30 days (staging), 90 days (production)
- Manifests stored with each backup for verification

### 3.3.5 Monitor Storage Usage and Costs

**Files:**
- `backend/services/r2_monitoring.py` - Monitoring service

**Monitoring Features:**
- Real-time storage metrics collection
- Cost estimation based on current usage
- Storage trend analysis
- Category-based storage breakdown (memes, templates, backups)

**Usage:**
```python
from backend.services.r2_monitoring import R2MonitoringService

monitor = R2MonitoringService()

# Get current metrics
metrics = monitor.get_storage_metrics()
print(f"Total size: {metrics.total_size_gb} GB")
print(f"Meme storage: {metrics.meme_size_bytes} bytes")

# Estimate monthly cost
cost = monitor.estimate_monthly_cost(metrics)
print(f"Monthly cost: ${cost['total_estimated_monthly_cost']}")

# Analyze trends
trends = monitor.get_storage_trends([metrics1, metrics2])
print(f"Monthly growth: {trends['size_growth_gb']} GB")
```

**Storage Metrics:**
- Total objects and size
- Per-category breakdown (memes, templates, backups)
- Monthly cost estimation
- API request costs
- Growth trends

---

## Environment Configuration (4.1)

### 4.1.1-4.1.5 Environment Files

**Files Created:**
- `.env.production` - Production environment variables
- `.env.staging` - Staging environment variables
- `.env.example` - Development template (existing)

**Key Sections in Each File:**

#### Application Configuration
```bash
APP_NAME=MemeGPT API
ENVIRONMENT=production  # or staging, development
DEBUG=false  # Disabled in production
WORKERS=4  # FastAPI workers
```

#### Database Configuration
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_SSL_MODE=require  # Enforce SSL in production
```

#### Redis Configuration
```bash
REDIS_URL=redis://:password@host:6379/0
REDIS_MAX_CONNECTIONS=20
REDIS_SSL=true  # Enable in production
```

#### AI Services
```bash
OPENAI_API_KEY=sk-prod-...
OPENAI_MODEL=gpt-4-turbo  # Production model
ANTHROPIC_API_KEY=sk-ant-prod-...
```

#### Cloudflare R2
```bash
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=prod-key
R2_SECRET_ACCESS_KEY=prod-secret
R2_BUCKET_NAME=memegpt-images-prod
R2_PUBLIC_URL=https://cdn.memegpt.com
R2_BACKUP_ENABLED=true
R2_BACKUP_RETENTION_DAYS=90
```

#### Rate Limiting
```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_FREE_REQUESTS=10
RATE_LIMIT_PRO_REQUESTS=500
RATE_LIMIT_API_REQUESTS=1000
```

#### Stripe Configuration
```bash
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

**Loading Environment:**
```bash
# Development
cp .env.example .env
# Staging
cp .env.staging .env
# Production
cp .env.production .env
```

---

## Docker & Deployment (4.2)

### 4.2.1-4.2.2 Docker Configuration

**Files:**
- `docker-compose.yml` - Enhanced with production-ready configuration
- `backend/Dockerfile` - Application container

**Docker Compose Services:**
1. **PostgreSQL** - Primary database
   - Health checks enabled
   - Persistent volume
   - SSL configuration
   - Logging drivers configured

2. **Redis** - Cache and job queue
   - Memory limits: 512MB
   - Persistence enabled (AOF)
   - Health checks
   - Password protection

3. **Backend** - FastAPI application
   - Auto-restart policy
   - Health endpoint checks
   - Volume mounts for static assets
   - Comprehensive logging

4. **Worker** - ARQ background job processor
   - Concurrent job processing
   - Redis-backed queue
   - Database connectivity
   - Health monitoring

5. **Frontend** - Optional React development server
   - Dev environment support
   - Hot reload capability

6. **Prometheus** - Metrics collection (optional, use `--profile monitoring`)
7. **Grafana** - Visualization (optional, use `--profile monitoring`)

**Launch Commands:**
```bash
# Development
docker-compose up -d

# With monitoring
docker-compose --profile monitoring up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

### 4.2.3 Setup Production Deployment Scripts

**Files:**
- `scripts/deploy.sh` - Unix/Linux deployment script
- `scripts/deploy.bat` - Windows deployment script

**Deployment Script Features:**
- Multi-environment support (production, staging, development)
- Automatic database backups before deployment
- Docker image building
- Database migration execution
- Health check verification
- Rollback capability
- Comprehensive logging

**Usage:**
```bash
# Linux/macOS
./scripts/deploy.sh production deploy
./scripts/deploy.sh staging deploy
./scripts/deploy.sh staging rollback
./scripts/deploy.sh staging healthcheck

# Windows
scripts\deploy.bat production deploy
scripts\deploy.bat staging deploy
scripts\deploy.bat staging rollback
```

**Script Operations:**
1. **Validation** - Check environment and dependencies
2. **Backup** - Create database snapshot
3. **Build** - Docker image compilation
4. **Deploy** - Start services
5. **Migrate** - Run Alembic migrations
6. **Verify** - Health checks

### 4.2.4 Configure Health Checks for All Services

**Health Check Endpoints:**
```
Backend:   GET /api/health
Database:  pg_isready
Redis:     redis-cli PING
Worker:    Redis connectivity check
```

**Docker Compose Health Configuration:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

**Health Status Values:**
- `starting` - Container initializing
- `healthy` - Service responding correctly
- `unhealthy` - Service failing health checks

### 4.2.5 Implement Logging and Monitoring

**Logging Configuration:**
- JSON-formatted logs for structured analysis
- Per-service log rotation (max 10MB, 3-5 files)
- LOG_LEVEL environment variable control
- Sentry integration for error tracking

**Monitoring Stack:**
- **Prometheus** - Metrics scraping
- **Grafana** - Visualization and dashboards
- **Alert Rules** - Critical condition detection

**Monitoring Files:**
- `monitoring/prometheus.yml` - Scrape configuration
- `monitoring/alert_rules.yml` - Alert definitions

**Available Metrics:**
- HTTP request rate and latency
- Error rates by status code
- Database connection pool usage
- Redis memory and evictions
- Job queue backlogs
- Meme generation success/failure rates

---

## Security Configuration (4.3)

### 4.3.1 Setup HTTPS Certificates and Redirects

**Configuration:**
- Production enforces HTTPS redirects
- Strict-Transport-Security header (HSTS)
- HSTS preload support
- SSL certificate configuration via environment

**Environment Variables:**
```bash
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
```

**Nginx/Reverse Proxy Example:**
```nginx
server {
    listen 443 ssl http2;
    server_name api.memegpt.com;
    
    ssl_certificate /etc/ssl/certs/memegpt.com.crt;
    ssl_certificate_key /etc/ssl/private/memegpt.com.key;
    
    # Redirect HTTP to HTTPS
    if ($scheme != "https") {
        return 301 https://$server_name$request_uri;
    }
    
    proxy_pass http://backend:8000;
}
```

### 4.3.2 Configure CORS Policies for Production

**Files:**
- `backend/core/cors.py` - CORS configuration

**CORS Settings by Environment:**
```python
# Production
CORS_ORIGINS = ["https://memegpt.com", "https://www.memegpt.com"]
CORS_ALLOW_CREDENTIALS = true
CORS_MAX_AGE = 600

# Staging
CORS_ORIGINS = ["https://staging.memegpt.com"]

# Development
CORS_ORIGINS = ["http://localhost:3000"]
```

**Configuration:**
- Origin validation
- Allowed methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
- Credentials support for authenticated requests
- Custom header allowlist
- Preflight cache (600 seconds)

### 4.3.3 Implement Input Validation and Sanitization

**Current Implementation:**
- Pydantic models for automatic validation
- Type checking on all endpoints
- Required field validation
- Length constraints

**Recommendations:**
```python
from pydantic import BaseModel, Field, validator

class MemeRequest(BaseModel):
    template_id: str = Field(..., min_length=1, max_length=100)
    text: str = Field(..., min_length=1, max_length=500)
    
    @validator('template_id')
    def validate_template_id(cls, v):
        # Custom validation logic
        if not v.isalnum():
            raise ValueError('Invalid template ID')
        return v
```

### 4.3.4 Setup Rate Limiting and DDoS Protection

**Rate Limiting Configuration:**
- Free tier: 10 requests/hour
- Pro tier: 500 requests/hour
- API tier: 1000 requests/hour
- Per-IP fallback limiting

**Files:**
- `backend/services/rate_limit.py` - Rate limiter implementation
- `backend/core/middleware.py` - RateLimitMiddleware

**DDoS Protection Layers:**
1. **Cloudflare DDoS Protection** - Upstream filtering
2. **Rate Limiting** - Request throttling
3. **Request Validation** - Malformed request rejection
4. **IP Reputation** - Suspicious source blocking

**Environment Variables:**
```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_WINDOW=3600
RATE_LIMIT_STORAGE=redis
```

### 4.3.5 Configure Secure Headers and CSP

**Files:**
- `backend/core/middleware.py` - SecurityHeadersMiddleware

**Security Headers Implemented:**
```
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
X-Frame-Options: DENY (production), SAMEORIGIN (staging)
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Content-Security-Policy: [comprehensive policy]
Referrer-Policy: strict-origin-when-cross-origin
```

**Content Security Policy:**
- Default: 'self' (own resources only)
- Scripts: 'self', 'unsafe-inline', 'unsafe-eval'
- Styles: 'self', 'unsafe-inline'
- Images: 'self', data:, https:, blob:
- Fonts: 'self', data:
- Connections: 'self', https:

**Middleware Code:**
```python
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response
```

---

## Deployment Instructions

### Prerequisites
- Docker and Docker Compose installed
- Environment variables configured
- SSL certificates (for production)
- Cloudflare R2 credentials
- OpenAI/Anthropic API keys

### Quick Start

**1. Prepare Environment**
```bash
# Copy appropriate environment file
cp backend/.env.production backend/.env
# OR for staging
cp backend/.env.staging backend/.env

# Edit and add secrets
nano backend/.env
```

**2. Deploy with Script**
```bash
# Linux/macOS
chmod +x scripts/deploy.sh
./scripts/deploy.sh production deploy

# Windows
scripts\deploy.bat production deploy
```

**3. Verify Deployment**
```bash
# Check service health
docker-compose ps

# View logs
docker-compose logs backend worker

# Test API
curl http://localhost:8000/api/health
```

**4. Run Migrations**
```bash
docker-compose exec backend python -m alembic upgrade head
```

### Manual Deployment Steps

**1. Build Images**
```bash
docker-compose build backend worker frontend
```

**2. Start Infrastructure**
```bash
docker-compose up -d postgres redis
```

**3. Wait for Health**
```bash
docker-compose exec postgres pg_isready -U memegpt -d memegpt
```

**4. Start Application**
```bash
docker-compose up -d backend worker
```

**5. Run Migrations**
```bash
docker-compose exec backend alembic upgrade head
```

**6. Verify Services**
```bash
docker-compose exec backend curl http://localhost:8000/api/health
```

---

## Monitoring & Logging

### Access Monitoring Stack
```bash
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3001 (admin/admin default)
# API Docs: http://localhost:8000/docs
```

### View Application Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f worker

# Follow new logs
docker-compose logs -f --tail=100
```

### Key Metrics to Monitor
- HTTP response time (p50, p95, p99)
- Error rate (5xx responses)
- Job processing success rate
- Database connection pool usage
- Redis memory utilization
- Storage usage and growth

### Common Issues and Resolution

**Backend won't start:**
```bash
# Check logs
docker-compose logs backend

# Verify database connectivity
docker-compose exec postgres pg_isready -U memegpt

# Check environment variables
docker-compose config | grep DATABASE_URL
```

**High memory usage:**
```bash
# Check Redis memory
docker-compose exec redis redis-cli INFO memory

# Check container limits
docker stats
```

**Job queue backlog:**
```bash
# Check job queue size
docker-compose exec redis redis-cli LLEN arq:queue

# Monitor worker logs
docker-compose logs -f worker
```

---

## Production Checklist

- [ ] Environment variables configured with real secrets
- [ ] SSL certificates installed and configured
- [ ] Database backups automated
- [ ] R2 storage backup strategy enabled
- [ ] Monitoring stack deployed
- [ ] Alert rules configured
- [ ] Rate limiting parameters tuned
- [ ] CORS origins restricted to production domains
- [ ] Security headers verified
- [ ] Database connection pool size optimized
- [ ] Redis memory limits set appropriately
- [ ] Log retention policies configured
- [ ] Disaster recovery procedures documented
- [ ] Load testing completed
- [ ] Security audit completed

---

## References

- FastAPI Documentation: https://fastapi.tiangolo.com
- Docker Compose: https://docs.docker.com/compose/
- Prometheus: https://prometheus.io
- Cloudflare R2: https://www.cloudflare.com/products/r2/
- PostgreSQL: https://www.postgresql.org
- Redis: https://redis.io
