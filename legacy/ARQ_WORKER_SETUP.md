# ARQ Worker Queue Setup for Async Meme Generation

## Overview

The ARQ (Async Redis Queue) worker system has been successfully implemented for handling asynchronous meme generation in MemeGPT v2. This system allows the API to handle multiple concurrent meme generation requests without blocking, providing a scalable solution for the production environment.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │───▶│   Redis Queue   │───▶│   ARQ Worker    │
│                 │    │                 │    │                 │
│ - Enqueue jobs  │    │ - Job storage   │    │ - Process jobs  │
│ - Poll status   │    │ - Status track  │    │ - Generate memes│
│ - Return results│    │ - Result cache  │    │ - Update status │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │   Redis Cache   │    │   OpenAI API    │
│                 │    │                 │    │                 │
│ - Job records   │    │ - Rate limits   │    │ - GPT-4o calls  │
│ - Meme storage  │    │ - Session data  │    │ - Text generation│
│ - User data     │    │ - Queue data    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Key Components

### 1. ARQ Worker Service (`backend/services/worker.py`)

**Enhanced Features:**
- ✅ Robust error handling and logging
- ✅ Database transaction management
- ✅ Job status tracking and updates
- ✅ Connection pooling and reuse
- ✅ Automatic retry mechanisms
- ✅ Queue statistics and monitoring
- ✅ Old job cleanup functionality
- ✅ Graceful shutdown handling

**Key Functions:**
- `enqueue_meme_generation()` - Enqueue new meme generation jobs
- `process_meme_generation()` - Worker function to process jobs
- `get_job_status()` - Retrieve job status and results
- `get_queue_stats()` - Monitor queue performance
- `cleanup_old_jobs()` - Maintain database hygiene

### 2. Job Status API (`backend/routers/jobs.py`)

**Endpoints:**
- `GET /api/jobs/{job_id}` - Get job status and results
- `GET /api/jobs/queue/stats` - Get queue statistics
- `POST /api/jobs/queue/cleanup` - Clean up old jobs

### 3. Database Models (`backend/models/models.py`)

**MemeJob Model:**
```python
class MemeJob(Base):
    id: str                    # Unique job identifier
    user_id: Optional[str]     # User who created the job
    prompt: str                # Meme generation prompt
    status: str                # "pending", "processing", "completed", "failed"
    result_meme_ids: List[str] # IDs of generated memes
    error_message: Optional[str] # Error details if failed
    created_at: datetime       # Job creation time
    updated_at: datetime       # Last status update
```

### 4. Worker Startup Script (`run_worker.py`)

**Features:**
- ✅ Dependency validation
- ✅ Health checks
- ✅ Graceful shutdown
- ✅ Signal handling
- ✅ Comprehensive logging
- ✅ Error recovery

## Configuration

### Environment Variables

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0
ARQ_REDIS_SETTINGS=redis://localhost:6379/1

# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost/memegpt

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key

# Cloudflare R2 Configuration (optional)
R2_ACCESS_KEY=your-r2-access-key
R2_SECRET_KEY=your-r2-secret-key
R2_BUCKET_NAME=memegpt-images
R2_ENDPOINT_URL=https://your-account.r2.cloudflarestorage.com
R2_PUBLIC_URL=https://pub-your-bucket.r2.dev
```

### ARQ Worker Settings

```python
class WorkerSettings:
    functions = [process_meme_generation]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10              # Maximum concurrent jobs
    job_timeout = 300          # 5 minutes per job
    keep_result = 3600         # Keep results for 1 hour
    queue_name = 'meme_generation'
    max_tries = 3              # Retry failed jobs 3 times
    retry_delay = 30           # 30 seconds between retries
```

## Usage

### 1. Starting the Worker

**Development:**
```bash
python run_worker.py
```

**Production (Docker):**
```bash
docker-compose up worker
```

**Direct ARQ command:**
```bash
arq backend.services.worker.WorkerSettings
```

### 2. API Usage

**Enqueue a meme generation job:**
```python
# POST /api/memes/generate
{
    "prompt": "A funny meme about cats"
}

# Response:
{
    "job_id": "uuid-string",
    "remaining_generations": 4
}
```

**Poll job status:**
```python
# GET /api/jobs/{job_id}

# Response (pending):
{
    "id": "uuid-string",
    "status": "pending",
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
}

# Response (completed):
{
    "id": "uuid-string",
    "status": "completed",
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:05Z",
    "memes": [
        {
            "id": "meme-uuid",
            "template_name": "Drake Hotline Bling",
            "template_id": 0,
            "meme_text": ["Ignoring cats", "Loving cats"],
            "image_url": "https://cdn.example.com/meme.png",
            "created_at": "2024-01-01T12:00:05Z"
        }
    ]
}
```

### 3. Frontend Integration

**JavaScript polling example:**
```javascript
async function generateMeme(prompt) {
    // Enqueue job
    const response = await fetch('/api/memes/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
    });
    
    const { job_id } = await response.json();
    
    // Poll for completion
    return await pollJobStatus(job_id);
}

async function pollJobStatus(jobId, maxAttempts = 30) {
    for (let i = 0; i < maxAttempts; i++) {
        const response = await fetch(`/api/jobs/${jobId}`);
        const job = await response.json();
        
        if (job.status === 'completed') {
            return job.memes;
        } else if (job.status === 'failed') {
            throw new Error(job.error || 'Job failed');
        }
        
        // Wait 2 seconds before next poll
        await new Promise(resolve => setTimeout(resolve, 2000));
    }
    
    throw new Error('Job timeout');
}
```

## Monitoring and Health Checks

### 1. Health Check Endpoints

**API Health:**
```bash
curl http://localhost:8000/health
# Response: {"status": "ok", "version": "2.0.0"}
```

**Worker Health:**
```bash
curl http://localhost:8000/health/worker
# Response: {
#   "status": "healthy",
#   "queue_stats": {
#     "queue_length": 2,
#     "pending_jobs": 1,
#     "processing_jobs": 1,
#     "completed_jobs": 150,
#     "failed_jobs": 3,
#     "total_jobs": 155
#   }
# }
```

### 2. Queue Statistics

```bash
curl http://localhost:8000/api/jobs/queue/stats
```

### 3. Log Monitoring

**Worker logs:**
```bash
docker logs memegpt-worker -f
```

**Key log patterns to monitor:**
- `ARQ worker starting up...` - Worker startup
- `Starting job: {job_id}` - Job processing begins
- `Job {job_id}: Completed successfully` - Job completion
- `Job {job_id}: {error_msg}` - Job errors

## Troubleshooting

### Common Issues

**1. Redis Connection Failed**
```bash
# Check Redis is running
docker ps | grep redis
redis-cli ping

# Check Redis URL configuration
echo $REDIS_URL
```

**2. Worker Not Processing Jobs**
```bash
# Check worker logs
docker logs memegpt-worker

# Check queue stats
curl http://localhost:8000/api/jobs/queue/stats

# Restart worker
docker-compose restart worker
```

**3. Jobs Stuck in Processing**
```bash
# Check for zombie jobs (processing > 5 minutes)
# Manual cleanup may be needed in database

# Restart worker to clear stuck jobs
docker-compose restart worker
```

**4. OpenAI API Errors**
```bash
# Check API key configuration
echo $OPENAI_API_KEY

# Check OpenAI service status
curl https://status.openai.com/

# Review worker logs for API errors
docker logs memegpt-worker | grep -i openai
```

### Performance Tuning

**1. Adjust Worker Concurrency**
```python
# In WorkerSettings
max_jobs = 20  # Increase for more concurrent jobs
```

**2. Optimize Job Timeout**
```python
# In WorkerSettings
job_timeout = 600  # Increase for complex memes
```

**3. Redis Memory Optimization**
```bash
# In docker-compose.yml
command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

## Testing

### 1. Run Test Suite

```bash
python test_arq_worker.py
```

### 2. Manual Testing

```bash
# Test Redis connection
redis-cli ping

# Test worker startup
python run_worker.py

# Test API endpoints
curl -X POST http://localhost:8000/api/memes/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Test meme about testing"}'
```

## Deployment Checklist

- [ ] Redis server is running and accessible
- [ ] PostgreSQL database is configured and migrated
- [ ] Environment variables are set correctly
- [ ] Required directories exist (templates, fonts, output)
- [ ] meme_data.json is available
- [ ] OpenAI API key is valid
- [ ] Worker process starts without errors
- [ ] Health check endpoints return healthy status
- [ ] Test job completes successfully
- [ ] Monitoring and logging are configured

## Security Considerations

1. **Redis Security:**
   - Use Redis AUTH if exposed to network
   - Configure firewall rules for Redis port
   - Use separate Redis databases for different environments

2. **API Security:**
   - Rate limiting is enforced before job enqueueing
   - User authentication is validated for protected endpoints
   - Input validation prevents malicious prompts

3. **Worker Security:**
   - Worker runs with minimal privileges
   - Temporary files are cleaned up after processing
   - Error messages don't expose sensitive information

## Performance Metrics

**Expected Performance:**
- Job enqueueing: < 100ms
- Meme generation: 10-30 seconds per job
- Job status polling: < 50ms
- Queue throughput: 10-50 jobs/minute (depending on complexity)

**Scaling Recommendations:**
- Single worker: Up to 100 jobs/hour
- Multiple workers: Linear scaling with worker count
- Redis: Can handle 1000+ jobs/second
- Database: Optimize with proper indexing on job_id and status fields

## Conclusion

The ARQ worker queue system is now fully implemented and production-ready for MemeGPT v2. It provides:

✅ **Scalable async processing** - Handle multiple concurrent requests
✅ **Robust error handling** - Graceful failure recovery and retry logic  
✅ **Comprehensive monitoring** - Health checks and queue statistics
✅ **Production deployment** - Docker containerization and orchestration
✅ **Developer experience** - Easy testing and debugging tools

The system is ready for production deployment and can scale to handle increased user load as the platform grows.