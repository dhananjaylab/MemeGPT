"""
Health check endpoints for monitoring application and dependency status.

This module provides comprehensive health monitoring for:
- Application status
- Database connectivity
- Redis connectivity and queue status
- OpenAI API connectivity
- Worker queue health
- System resource monitoring
"""

import asyncio
import time
import psutil
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import redis.asyncio as redis
from openai import AsyncOpenAI

from core.config import settings
from db.session import AsyncSessionLocal, engine
from services.worker import get_arq_pool, get_queue_stats

router = APIRouter()


class HealthChecker:
    """Centralized health checking service"""
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self._redis_client: Optional[redis.Redis] = None
    
    async def get_redis_client(self) -> redis.Redis:
        """Get Redis client with connection reuse"""
        if self._redis_client is None:
            self._redis_client = redis.from_url(settings.redis_url)
        return self._redis_client
    
    async def close_redis_client(self):
        """Close Redis client connection"""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and basic operations"""
        start_time = time.time()
        
        try:
            async with AsyncSessionLocal() as db:
                # Test basic connectivity
                result = await db.execute(text("SELECT 1"))
                result.scalar()
                
                # Test table existence
                tables_result = await db.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                tables = [row[0] for row in tables_result.fetchall()]
                
                # Check if core tables exist
                required_tables = ['users', 'memes', 'meme_jobs']
                missing_tables = [table for table in required_tables if table not in tables]
                
                response_time = round((time.time() - start_time) * 1000, 2)
                
                return {
                    "status": "healthy" if not missing_tables else "degraded",
                    "response_time_ms": response_time,
                    "tables_found": len(tables),
                    "required_tables": required_tables,
                    "missing_tables": missing_tables,
                    "connection_pool_size": engine.pool.size(),
                    "checked_out_connections": engine.pool.checkedout(),
                }
                
        except SQLAlchemyError as e:
            response_time = round((time.time() - start_time) * 1000, 2)
            return {
                "status": "unhealthy",
                "response_time_ms": response_time,
                "error": str(e),
                "error_type": "database_error"
            }
        except Exception as e:
            response_time = round((time.time() - start_time) * 1000, 2)
            return {
                "status": "unhealthy",
                "response_time_ms": response_time,
                "error": str(e),
                "error_type": "unexpected_error"
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and basic operations"""
        start_time = time.time()
        
        try:
            redis_client = await self.get_redis_client()
            
            # Test basic connectivity
            await redis_client.ping()
            
            # Test basic operations
            test_key = "health_check_test"
            await redis_client.set(test_key, "test_value", ex=10)
            test_value = await redis_client.get(test_key)
            await redis_client.delete(test_key)
            
            # Get Redis info
            info = await redis_client.info()
            
            response_time = round((time.time() - start_time) * 1000, 2)
            
            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "test_operation": "success" if test_value == b"test_value" else "failed"
            }
            
        except redis.ConnectionError as e:
            response_time = round((time.time() - start_time) * 1000, 2)
            return {
                "status": "unhealthy",
                "response_time_ms": response_time,
                "error": str(e),
                "error_type": "connection_error"
            }
        except Exception as e:
            response_time = round((time.time() - start_time) * 1000, 2)
            return {
                "status": "unhealthy",
                "response_time_ms": response_time,
                "error": str(e),
                "error_type": "unexpected_error"
            }
    
    async def check_openai_api(self) -> Dict[str, Any]:
        """Check OpenAI API connectivity"""
        start_time = time.time()
        
        if not self.openai_client:
            return {
                "status": "not_configured",
                "response_time_ms": 0,
                "error": "OpenAI API key not configured"
            }
        
        try:
            # Test with a minimal request
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=1,
                temperature=0
            )
            
            response_time = round((time.time() - start_time) * 1000, 2)
            
            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                }
            }
            
        except Exception as e:
            response_time = round((time.time() - start_time) * 1000, 2)
            return {
                "status": "unhealthy",
                "response_time_ms": response_time,
                "error": str(e),
                "error_type": "api_error"
            }
    
    async def check_worker_queue(self) -> Dict[str, Any]:
        """Check ARQ worker queue health"""
        start_time = time.time()
        
        try:
            # Get queue statistics
            stats = await get_queue_stats()
            
            # Check ARQ pool connectivity
            pool = await get_arq_pool()
            await pool.ping()
            
            response_time = round((time.time() - start_time) * 1000, 2)
            
            # Determine health status based on queue metrics
            status = "healthy"
            if "error" in stats:
                status = "unhealthy"
            elif stats.get("queue_length", 0) > 100:  # High queue backlog
                status = "degraded"
            elif stats.get("failed_jobs", 0) > stats.get("completed_jobs", 0):  # More failures than successes
                status = "degraded"
            
            return {
                "status": status,
                "response_time_ms": response_time,
                "queue_stats": stats,
                "pool_connected": True
            }
            
        except Exception as e:
            response_time = round((time.time() - start_time) * 1000, 2)
            return {
                "status": "unhealthy",
                "response_time_ms": response_time,
                "error": str(e),
                "error_type": "worker_error",
                "pool_connected": False
            }
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Determine status based on resource usage
            status = "healthy"
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                status = "critical"
            elif cpu_percent > 70 or memory.percent > 70 or disk.percent > 80:
                status = "degraded"
            
            return {
                "status": status,
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "percent": memory.percent,
                    "available_gb": round(memory.available / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2)
                },
                "disk": {
                    "percent": disk.percent,
                    "free_gb": round(disk.free / (1024**3), 2),
                    "total_gb": round(disk.total / (1024**3), 2)
                }
            }
            
        except Exception as e:
            return {
                "status": "unknown",
                "error": str(e),
                "error_type": "system_error"
            }


# Global health checker instance
health_checker = HealthChecker()


@router.get("/health")
async def basic_health():
    """Basic health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0",
        "environment": settings.environment
    }


@router.get("/health/detailed")
async def detailed_health():
    """Comprehensive health check for all dependencies"""
    start_time = time.time()
    
    # Run all health checks concurrently
    database_task = health_checker.check_database()
    redis_task = health_checker.check_redis()
    openai_task = health_checker.check_openai_api()
    worker_task = health_checker.check_worker_queue()
    system_task = health_checker.check_system_resources()
    
    # Wait for all checks to complete
    database_health, redis_health, openai_health, worker_health, system_health = await asyncio.gather(
        database_task, redis_task, openai_task, worker_task, system_task,
        return_exceptions=True
    )
    
    # Handle any exceptions from health checks
    def safe_result(result, service_name):
        if isinstance(result, Exception):
            return {
                "status": "error",
                "error": str(result),
                "error_type": "health_check_exception"
            }
        return result
    
    database_health = safe_result(database_health, "database")
    redis_health = safe_result(redis_health, "redis")
    openai_health = safe_result(openai_health, "openai")
    worker_health = safe_result(worker_health, "worker")
    system_health = safe_result(system_health, "system")
    
    # Determine overall status
    all_statuses = [
        database_health.get("status"),
        redis_health.get("status"),
        openai_health.get("status"),
        worker_health.get("status"),
        system_health.get("status")
    ]
    
    if any(status in ["unhealthy", "error", "critical"] for status in all_statuses):
        overall_status = "unhealthy"
    elif any(status == "degraded" for status in all_statuses):
        overall_status = "degraded"
    elif "not_configured" in all_statuses:
        overall_status = "partial"
    else:
        overall_status = "healthy"
    
    total_time = round((time.time() - start_time) * 1000, 2)
    
    response = {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0",
        "environment": settings.environment,
        "total_check_time_ms": total_time,
        "services": {
            "database": database_health,
            "redis": redis_health,
            "openai_api": openai_health,
            "worker_queue": worker_health,
            "system_resources": system_health
        }
    }
    
    # Return appropriate HTTP status code
    if overall_status == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response
        )
    elif overall_status in ["degraded", "partial"]:
        raise HTTPException(
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            detail=response
        )
    
    return response


@router.get("/health/database")
async def database_health():
    """Database-specific health check"""
    result = await health_checker.check_database()
    
    if result["status"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result
        )
    elif result["status"] == "degraded":
        raise HTTPException(
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            detail=result
        )
    
    return result


@router.get("/health/redis")
async def redis_health():
    """Redis-specific health check"""
    result = await health_checker.check_redis()
    
    if result["status"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result
        )
    
    return result


@router.get("/health/openai")
async def openai_health():
    """OpenAI API-specific health check"""
    result = await health_checker.check_openai_api()
    
    if result["status"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result
        )
    elif result["status"] == "not_configured":
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=result
        )
    
    return result


@router.get("/health/worker")
async def worker_health():
    """Worker queue-specific health check"""
    result = await health_checker.check_worker_queue()
    
    if result["status"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result
        )
    elif result["status"] == "degraded":
        raise HTTPException(
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            detail=result
        )
    
    return result


@router.get("/health/system")
async def system_health():
    """System resources health check"""
    result = await health_checker.check_system_resources()
    
    if result["status"] == "critical":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result
        )
    elif result["status"] == "degraded":
        raise HTTPException(
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            detail=result
        )
    
    return result


@router.get("/health/readiness")
async def readiness_check():
    """Kubernetes readiness probe - checks if app is ready to serve traffic"""
    # Check critical dependencies only
    database_health = await health_checker.check_database()
    redis_health = await health_checker.check_redis()
    
    if (database_health["status"] == "unhealthy" or 
        redis_health["status"] == "unhealthy"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "ready": False,
                "database": database_health["status"],
                "redis": redis_health["status"]
            }
        )
    
    return {
        "ready": True,
        "database": database_health["status"],
        "redis": redis_health["status"]
    }


@router.get("/health/liveness")
async def liveness_check():
    """Kubernetes liveness probe - checks if app is alive"""
    return {
        "alive": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Cleanup function for graceful shutdown
async def cleanup_health_checker():
    """Cleanup health checker resources"""
    await health_checker.close_redis_client()