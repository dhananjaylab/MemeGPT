# Rate Limiting and Performance Tuning Guide

## Rate Limiting Configuration

### Overview

MemeGPT implements sliding-window rate limiting with per-tier configuration and IP-based fallback.

### Tier Configuration

#### Free Tier
- **Requests per hour**: 10
- **Burst limit**: 2 requests per minute
- **Use case**: Anonymous/trial users

#### Pro Tier
- **Requests per hour**: 500
- **Burst limit**: 50 requests per minute
- **Use case**: Paid subscribers

#### API Tier
- **Requests per hour**: 1000
- **Burst limit**: 100 requests per minute
- **Use case**: Developers with API keys

### Environment Variables

```bash
# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=1000  # Global burst
RATE_LIMIT_WINDOW=3600    # 1 hour window
RATE_LIMIT_STORAGE=redis  # Backend storage

# Tier-specific limits
RATE_LIMIT_FREE_REQUESTS=10
RATE_LIMIT_PRO_REQUESTS=500
RATE_LIMIT_API_REQUESTS=1000
```

### Configuration by Endpoint

```python
# backend/core/middleware.py

RATE_LIMIT_CONFIG = {
    # Meme generation - CPU intensive
    "/api/memes/generate": {
        "free": 5,      # per hour
        "pro": 100,     # per hour
        "api": 500,     # per hour
    },
    
    # Job creation - Important
    "/api/jobs": {
        "free": 10,
        "pro": 200,
        "api": 1000,
    },
    
    # Gallery - Read-heavy
    "/api/gallery": {
        "free": 50,
        "pro": 1000,
        "api": 5000,
    },
    
    # Auth endpoints - Security critical
    "/api/auth/login": {
        "free": 5,
        "pro": 20,
        "api": 20,
    },
}
```

## Sliding Window Algorithm

```python
from backend.services.rate_limit import rate_limit_request

# Implementation
class SlidingWindowRateLimiter:
    async def is_allowed(self, user_id, limit, window_seconds=3600):
        """Check if request is allowed"""
        key = f"rate_limit:{user_id}"
        
        # Get current count within window
        count = await redis.zcard(key)
        
        if count < limit:
            # Add request timestamp
            await redis.zadd(key, {time.time(): 1})
            # Set expiration
            await redis.expire(key, window_seconds)
            return True, limit - count - 1
        
        return False, 0
```

## Response Headers

Rate limit information is included in response headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640000000
Retry-After: 3600
```

## Handling Rate Limit Errors

### HTTP 429 Response
```json
{
  "detail": "Rate limit exceeded",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 3600,
  "limit": 100,
  "remaining": 0
}
```

### Client-side Handling
```typescript
// frontend/lib/api.ts

async function handleRequest(url, options) {
  try {
    const response = await fetch(url, options);
    
    if (response.status === 429) {
      const retryAfter = response.headers.get('Retry-After');
      
      // Show user message
      showToast({
        type: 'error',
        message: `Rate limited. Try again in ${retryAfter}s`
      });
      
      // Exponential backoff
      await exponentialBackoff(retryAfter);
    }
    
    return response;
  } catch (error) {
    // Handle error
  }
}
```

## Fine-Tuning for Your Usage

### Analyzing Request Patterns
```python
# backend/services/analytics.py

async def analyze_rate_limit_usage():
    """Analyze current rate limit usage"""
    from backend.services.rate_limit import get_usage_stats
    
    stats = await get_usage_stats()
    
    # By user tier
    for tier, data in stats.items():
        avg_requests = data['total_requests'] / len(data['users'])
        peak_requests = data['max_requests_in_minute']
        
        print(f"{tier}: avg {avg_requests}, peak {peak_requests}")
```

### Adjustment Recommendations

#### High Usage Patterns
If users frequently hit rate limits:
```bash
# Increase limits
RATE_LIMIT_FREE_REQUESTS=20
RATE_LIMIT_PRO_REQUESTS=750
```

#### Abuse Patterns
If abuse detected:
```bash
# Decrease limits
RATE_LIMIT_FREE_REQUESTS=5
# Or implement IP-based blocking
```

#### Burst Traffic
For expected traffic spikes:
```bash
# Increase burst allowance
RATE_LIMIT_BURST_MULTIPLIER=1.5  # 50% more burst
```

## Advanced Configuration

### Distributed Rate Limiting
```python
# Multi-instance setup
from aioredis_cluster import RedisCluster

# Use Redis Cluster for distributed limiting
redis_cluster = await RedisCluster.create(
    [("127.0.0.1", 6379), ("127.0.0.1", 6380)],
)

# Rate limiter automatically uses cluster
limiter = RateLimiter(redis_cluster)
```

### Custom Rate Limiting Rules
```python
class CustomRateLimiter(RateLimiter):
    async def get_limit(self, user_id, endpoint):
        # Premium users get 2x limits
        user = await get_user(user_id)
        
        base_limit = self.TIER_LIMITS[user.tier][endpoint]
        
        if user.subscription == "premium":
            return base_limit * 2
        
        return base_limit
```

### Gradual Rate Limit Increase
```python
# Gradually increase limits as user proves reliability
def get_dynamic_limit(user_id, tier):
    user = get_user(user_id)
    base_limit = TIER_LIMITS[tier]
    
    # Increase 10% per day of good behavior
    days_active = (now() - user.created_at).days
    multiplier = min(1.5, 1.0 + (days_active * 0.1))
    
    return int(base_limit * multiplier)
```

## Monitoring Rate Limits

### Key Metrics
```python
# Metrics to track
- Rate limit hits per endpoint
- Rate limit hits per user tier
- Average requests per user
- Peak requests per minute
- Abuse attempts detected
```

### Prometheus Metrics
```yaml
# monitoring/prometheus.yml
rate_limit_exceeded_total{endpoint, tier}
rate_limit_remaining{user_id}
rate_limit_reset_time{user_id}
```

### Grafana Dashboard
Create dashboards to visualize:
- Rate limit usage by tier
- Endpoints with high limiting
- Users approaching limits
- Potential abuse patterns

## Debugging Rate Limit Issues

### Check User's Rate Limit Status
```python
async def check_user_limits(user_id):
    from backend.services.rate_limit import RateLimiter
    
    limiter = RateLimiter(redis)
    
    for endpoint in ["/api/memes/generate", "/api/jobs"]:
        is_allowed, remaining = await limiter.is_allowed(
            f"{user_id}:{endpoint}"
        )
        print(f"{endpoint}: {remaining} remaining")
```

### View Rate Limit in Redis
```bash
# Connect to Redis
redis-cli

# Check keys
KEYS "rate_limit:*"

# View specific user limit
ZRANGE "rate_limit:user123" 0 -1 WITHSCORES

# Check expiration
TTL "rate_limit:user123"
```

### Log Rate Limit Events
```python
# Enable debug logging
logging.getLogger('rate_limit').setLevel(logging.DEBUG)

# View logs
docker-compose logs -f backend | grep -i "rate_limit"
```

## Best Practices

### For Users
1. **Batch requests** - Combine multiple requests
2. **Implement backoff** - Respect Retry-After header
3. **Cache results** - Reuse previous responses
4. **Consider upgrade** - Higher tier = higher limits
5. **Schedule jobs** - Spread requests over time

### For Admins
1. **Monitor usage** - Track patterns continuously
2. **Set alerts** - Alert on unusual activity
3. **Adjust gradually** - Small incremental changes
4. **Document changes** - Keep audit trail
5. **Communicate** - Notify users of limit changes

### For Developers
1. **Test with limits** - Include rate limit tests
2. **Handle 429** - Implement proper backoff
3. **Log limits** - Track for debugging
4. **Optimize calls** - Reduce unnecessary requests
5. **Use caching** - Implement response caching

## Rate Limiting Exemptions

### Scenarios for Exemption
- Health check endpoints
- Internal services
- Webhook receivers
- Trusted partners

### Implementation
```python
# Exclude from rate limiting
RATE_LIMIT_EXEMPT_PATHS = [
    "/api/health",
    "/api/webhook",
    "/api/internal",
]

# Check in middleware
if request.url.path in RATE_LIMIT_EXEMPT_PATHS:
    return await call_next(request)
```

## Testing Rate Limits

```bash
# Load test rate limits
ab -n 150 -c 10 http://localhost:8000/api/memes/generate

# Monitor responses
# Count 429s: grep -c 429 results.txt

# Verify backoff behavior
for i in {1..20}; do
  curl http://localhost:8000/api/memes/generate
  sleep 1
done
```

