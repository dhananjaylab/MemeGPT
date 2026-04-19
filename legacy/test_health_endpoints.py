"""
Test suite for health check endpoints.

This module tests all health check functionality including:
- Basic health checks
- Detailed dependency monitoring
- Individual service health checks
- Kubernetes readiness/liveness probes
- Error handling and status codes
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

from backend.main import app
from backend.routers.health import HealthChecker


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Async test client fixture"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def health_checker():
    """Health checker instance fixture"""
    return HealthChecker()


class TestBasicHealthEndpoints:
    """Test basic health check endpoints"""
    
    def test_basic_health_check(self, client):
        """Test basic health endpoint returns OK"""
        response = client.get("/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "version" in data
        assert "environment" in data
    
    def test_liveness_probe(self, client):
        """Test Kubernetes liveness probe"""
        response = client.get("/api/health/liveness")
        assert response.status_code == 200
        
        data = response.json()
        assert data["alive"] is True
        assert "timestamp" in data


class TestDatabaseHealthCheck:
    """Test database health check functionality"""
    
    @patch('backend.routers.health.AsyncSessionLocal')
    async def test_database_health_success(self, mock_session, health_checker):
        """Test successful database health check"""
        # Mock successful database operations
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db
        
        # Mock query results
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_db.execute.return_value = mock_result
        
        # Mock tables query
        mock_tables_result = MagicMock()
        mock_tables_result.fetchall.return_value = [('users',), ('memes',), ('meme_jobs',)]
        mock_db.execute.side_effect = [mock_result, mock_tables_result]
        
        # Mock engine pool
        with patch('backend.routers.health.engine') as mock_engine:
            mock_engine.pool.size.return_value = 10
            mock_engine.pool.checkedout.return_value = 2
            
            result = await health_checker.check_database()
            
            assert result["status"] == "healthy"
            assert result["response_time_ms"] > 0
            assert result["tables_found"] == 3
            assert result["missing_tables"] == []
            assert result["connection_pool_size"] == 10
            assert result["checked_out_connections"] == 2
    
    @patch('backend.routers.health.AsyncSessionLocal')
    async def test_database_health_missing_tables(self, mock_session, health_checker):
        """Test database health check with missing tables"""
        # Mock database with missing tables
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_db
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        
        mock_tables_result = MagicMock()
        mock_tables_result.fetchall.return_value = [('users',)]  # Missing memes and meme_jobs
        mock_db.execute.side_effect = [mock_result, mock_tables_result]
        
        with patch('backend.routers.health.engine') as mock_engine:
            mock_engine.pool.size.return_value = 10
            mock_engine.pool.checkedout.return_value = 2
            
            result = await health_checker.check_database()
            
            assert result["status"] == "degraded"
            assert result["missing_tables"] == ["memes", "meme_jobs"]
    
    @patch('backend.routers.health.AsyncSessionLocal')
    async def test_database_health_connection_error(self, mock_session, health_checker):
        """Test database health check with connection error"""
        # Mock connection error
        mock_session.return_value.__aenter__.side_effect = Exception("Connection failed")
        
        result = await health_checker.check_database()
        
        assert result["status"] == "unhealthy"
        assert "error" in result
        assert result["error_type"] == "unexpected_error"


class TestRedisHealthCheck:
    """Test Redis health check functionality"""
    
    @patch('backend.routers.health.redis.from_url')
    async def test_redis_health_success(self, mock_redis_from_url, health_checker):
        """Test successful Redis health check"""
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis_from_url.return_value = mock_redis
        
        # Mock Redis operations
        mock_redis.ping.return_value = True
        mock_redis.set.return_value = True
        mock_redis.get.return_value = b"test_value"
        mock_redis.delete.return_value = 1
        
        # Mock Redis info
        mock_redis.info.return_value = {
            "redis_version": "6.2.0",
            "connected_clients": 5,
            "used_memory_human": "1.2M",
            "keyspace_hits": 100,
            "keyspace_misses": 10
        }
        
        result = await health_checker.check_redis()
        
        assert result["status"] == "healthy"
        assert result["response_time_ms"] > 0
        assert result["redis_version"] == "6.2.0"
        assert result["connected_clients"] == 5
        assert result["test_operation"] == "success"
    
    @patch('backend.routers.health.redis.from_url')
    async def test_redis_health_connection_error(self, mock_redis_from_url, health_checker):
        """Test Redis health check with connection error"""
        # Mock connection error
        mock_redis = AsyncMock()
        mock_redis_from_url.return_value = mock_redis
        mock_redis.ping.side_effect = Exception("Connection refused")
        
        result = await health_checker.check_redis()
        
        assert result["status"] == "unhealthy"
        assert "error" in result
        assert result["error_type"] == "unexpected_error"


class TestOpenAIHealthCheck:
    """Test OpenAI API health check functionality"""
    
    async def test_openai_health_not_configured(self, health_checker):
        """Test OpenAI health check when API key not configured"""
        health_checker.openai_client = None
        
        result = await health_checker.check_openai_api()
        
        assert result["status"] == "not_configured"
        assert "OpenAI API key not configured" in result["error"]
    
    async def test_openai_health_success(self, health_checker):
        """Test successful OpenAI API health check"""
        # Mock OpenAI client
        mock_client = AsyncMock()
        health_checker.openai_client = mock_client
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.model = "gpt-4o"
        mock_response.usage.prompt_tokens = 5
        mock_response.usage.completion_tokens = 1
        mock_response.usage.total_tokens = 6
        
        mock_client.chat.completions.create.return_value = mock_response
        
        result = await health_checker.check_openai_api()
        
        assert result["status"] == "healthy"
        assert result["model"] == "gpt-4o"
        assert result["usage"]["total_tokens"] == 6
    
    async def test_openai_health_api_error(self, health_checker):
        """Test OpenAI health check with API error"""
        # Mock OpenAI client with error
        mock_client = AsyncMock()
        health_checker.openai_client = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        result = await health_checker.check_openai_api()
        
        assert result["status"] == "unhealthy"
        assert "error" in result
        assert result["error_type"] == "api_error"


class TestWorkerHealthCheck:
    """Test worker queue health check functionality"""
    
    @patch('backend.routers.health.get_queue_stats')
    @patch('backend.routers.health.get_arq_pool')
    async def test_worker_health_success(self, mock_get_pool, mock_get_stats, health_checker):
        """Test successful worker health check"""
        # Mock queue stats
        mock_get_stats.return_value = {
            "queue_length": 5,
            "pending_jobs": 2,
            "processing_jobs": 1,
            "completed_jobs": 100,
            "failed_jobs": 5,
            "total_jobs": 108
        }
        
        # Mock ARQ pool
        mock_pool = AsyncMock()
        mock_get_pool.return_value = mock_pool
        mock_pool.ping.return_value = True
        
        result = await health_checker.check_worker_queue()
        
        assert result["status"] == "healthy"
        assert result["pool_connected"] is True
        assert result["queue_stats"]["queue_length"] == 5
    
    @patch('backend.routers.health.get_queue_stats')
    @patch('backend.routers.health.get_arq_pool')
    async def test_worker_health_high_queue(self, mock_get_pool, mock_get_stats, health_checker):
        """Test worker health check with high queue backlog"""
        # Mock high queue length
        mock_get_stats.return_value = {
            "queue_length": 150,  # High backlog
            "pending_jobs": 150,
            "processing_jobs": 0,
            "completed_jobs": 50,
            "failed_jobs": 10,
            "total_jobs": 210
        }
        
        mock_pool = AsyncMock()
        mock_get_pool.return_value = mock_pool
        mock_pool.ping.return_value = True
        
        result = await health_checker.check_worker_queue()
        
        assert result["status"] == "degraded"
    
    @patch('backend.routers.health.get_queue_stats')
    async def test_worker_health_connection_error(self, mock_get_stats, health_checker):
        """Test worker health check with connection error"""
        mock_get_stats.side_effect = Exception("Connection failed")
        
        result = await health_checker.check_worker_queue()
        
        assert result["status"] == "unhealthy"
        assert result["pool_connected"] is False


class TestSystemHealthCheck:
    """Test system resources health check functionality"""
    
    @patch('backend.routers.health.psutil')
    async def test_system_health_success(self, mock_psutil, health_checker):
        """Test successful system health check"""
        # Mock system metrics
        mock_psutil.cpu_percent.return_value = 25.5
        mock_psutil.cpu_count.return_value = 4
        
        mock_memory = MagicMock()
        mock_memory.percent = 45.0
        mock_memory.available = 8 * (1024**3)  # 8GB
        mock_memory.total = 16 * (1024**3)     # 16GB
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.percent = 60.0
        mock_disk.free = 100 * (1024**3)      # 100GB
        mock_disk.total = 500 * (1024**3)     # 500GB
        mock_psutil.disk_usage.return_value = mock_disk
        
        result = await health_checker.check_system_resources()
        
        assert result["status"] == "healthy"
        assert result["cpu"]["percent"] == 25.5
        assert result["cpu"]["count"] == 4
        assert result["memory"]["percent"] == 45.0
        assert result["disk"]["percent"] == 60.0
    
    @patch('backend.routers.health.psutil')
    async def test_system_health_degraded(self, mock_psutil, health_checker):
        """Test system health check with degraded performance"""
        # Mock high resource usage
        mock_psutil.cpu_percent.return_value = 85.0  # High CPU
        mock_psutil.cpu_count.return_value = 4
        
        mock_memory = MagicMock()
        mock_memory.percent = 75.0  # High memory usage
        mock_memory.available = 2 * (1024**3)
        mock_memory.total = 16 * (1024**3)
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.percent = 85.0  # High disk usage
        mock_disk.free = 50 * (1024**3)
        mock_disk.total = 500 * (1024**3)
        mock_psutil.disk_usage.return_value = mock_disk
        
        result = await health_checker.check_system_resources()
        
        assert result["status"] == "degraded"
    
    @patch('backend.routers.health.psutil')
    async def test_system_health_critical(self, mock_psutil, health_checker):
        """Test system health check with critical resource usage"""
        # Mock critical resource usage
        mock_psutil.cpu_percent.return_value = 95.0  # Critical CPU
        mock_psutil.cpu_count.return_value = 4
        
        mock_memory = MagicMock()
        mock_memory.percent = 95.0  # Critical memory usage
        mock_memory.available = 0.5 * (1024**3)
        mock_memory.total = 16 * (1024**3)
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.percent = 95.0  # Critical disk usage
        mock_disk.free = 10 * (1024**3)
        mock_disk.total = 500 * (1024**3)
        mock_psutil.disk_usage.return_value = mock_disk
        
        result = await health_checker.check_system_resources()
        
        assert result["status"] == "critical"


class TestHealthEndpoints:
    """Test health check HTTP endpoints"""
    
    def test_database_health_endpoint_success(self, client):
        """Test database health endpoint with mocked success"""
        with patch('backend.routers.health.health_checker.check_database') as mock_check:
            mock_check.return_value = {"status": "healthy", "response_time_ms": 50}
            
            response = client.get("/api/health/database")
            assert response.status_code == 200
    
    def test_database_health_endpoint_unhealthy(self, client):
        """Test database health endpoint with unhealthy status"""
        with patch('backend.routers.health.health_checker.check_database') as mock_check:
            mock_check.return_value = {"status": "unhealthy", "error": "Connection failed"}
            
            response = client.get("/api/health/database")
            assert response.status_code == 503
    
    def test_readiness_probe_success(self, client):
        """Test Kubernetes readiness probe with healthy dependencies"""
        with patch('backend.routers.health.health_checker.check_database') as mock_db, \
             patch('backend.routers.health.health_checker.check_redis') as mock_redis:
            
            mock_db.return_value = {"status": "healthy"}
            mock_redis.return_value = {"status": "healthy"}
            
            response = client.get("/api/health/readiness")
            assert response.status_code == 200
            
            data = response.json()
            assert data["ready"] is True
    
    def test_readiness_probe_unhealthy(self, client):
        """Test Kubernetes readiness probe with unhealthy dependencies"""
        with patch('backend.routers.health.health_checker.check_database') as mock_db, \
             patch('backend.routers.health.health_checker.check_redis') as mock_redis:
            
            mock_db.return_value = {"status": "unhealthy"}
            mock_redis.return_value = {"status": "healthy"}
            
            response = client.get("/api/health/readiness")
            assert response.status_code == 503
    
    def test_detailed_health_endpoint(self, client):
        """Test detailed health endpoint with all services"""
        with patch('backend.routers.health.health_checker.check_database') as mock_db, \
             patch('backend.routers.health.health_checker.check_redis') as mock_redis, \
             patch('backend.routers.health.health_checker.check_openai_api') as mock_openai, \
             patch('backend.routers.health.health_checker.check_worker_queue') as mock_worker, \
             patch('backend.routers.health.health_checker.check_system_resources') as mock_system:
            
            # Mock all services as healthy
            mock_db.return_value = {"status": "healthy"}
            mock_redis.return_value = {"status": "healthy"}
            mock_openai.return_value = {"status": "healthy"}
            mock_worker.return_value = {"status": "healthy"}
            mock_system.return_value = {"status": "healthy"}
            
            response = client.get("/api/health/detailed")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
            assert "services" in data
            assert len(data["services"]) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])