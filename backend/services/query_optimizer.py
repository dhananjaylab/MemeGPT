"""
Database Query Optimization Service
Analyzes and optimizes database queries for performance
"""
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Query performance metrics"""
    query: str
    execution_time: float
    rows_affected: int
    indexes_used: List[str]
    optimization_suggestions: List[str]


class QueryOptimizer:
    """Analyzes and optimizes database queries"""
    
    # Common optimization patterns
    OPTIMIZATION_RULES = {
        "SELECT *": "Use specific columns instead of SELECT * for faster retrieval",
        "N+1 problem": "Use eager loading (joinedload) to avoid N+1 queries",
        "Large OFFSET": "Use keyset pagination instead of OFFSET for large datasets",
        "Full table scan": "Add appropriate indexes on WHERE clause columns",
        "Without ORDER BY": "Add ORDER BY for consistent pagination results",
        "COUNT(*)": "Use LIMIT with COUNT for large tables",
    }
    
    @staticmethod
    async def analyze_query(
        session: AsyncSession,
        query_str: str,
    ) -> QueryMetrics:
        """Analyze query performance"""
        start_time = time.time()
        
        try:
            # Get query plan
            explain_result = await session.execute(
                text(f"EXPLAIN ANALYZE {query_str}")
            )
            plan = explain_result.fetchall()
            
            execution_time = time.time() - start_time
            
            # Parse suggestions
            suggestions = QueryOptimizer._extract_suggestions(query_str, plan)
            
            return QueryMetrics(
                query=query_str,
                execution_time=execution_time,
                rows_affected=0,
                indexes_used=[],
                optimization_suggestions=suggestions,
            )
        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            raise
    
    @staticmethod
    def _extract_suggestions(query: str, plan: List) -> List[str]:
        """Extract optimization suggestions from query and plan"""
        suggestions = []
        query_upper = query.upper()
        
        # Check for common issues
        if "SELECT *" in query_upper:
            suggestions.append(QueryOptimizer.OPTIMIZATION_RULES["SELECT *"])
        
        if "OFFSET" in query_upper and "LIMIT" in query_upper:
            if "OFFSET" in query_upper and int(query_upper.split("OFFSET")[-1].split()[0]) > 10000:
                suggestions.append(QueryOptimizer.OPTIMIZATION_RULES["Large OFFSET"])
        
        if "COUNT(*)" in query_upper:
            suggestions.append("Consider using COUNT with LIMIT for large tables")
        
        if "LEFT JOIN" in query_upper and "ORDER BY" not in query_upper:
            suggestions.append("Add ORDER BY for consistent JOIN results")
        
        return suggestions
    
    @staticmethod
    def suggest_indexes(table_name: str, where_columns: List[str]) -> List[str]:
        """Suggest indexes for frequently filtered columns"""
        suggestions = []
        
        for column in where_columns:
            suggestions.append(f"CREATE INDEX idx_{table_name}_{column} ON {table_name}({column})")
        
        return suggestions


class CachingLayer:
    """Caching layer for frequently accessed data"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def get_or_fetch(
        self,
        key: str,
        fetch_func,
        ttl: int = 3600,
    ) -> Any:
        """Get from cache or fetch from database"""
        try:
            # Try cache
            cached = await self.redis.get(key)
            if cached:
                logger.debug(f"Cache hit: {key}")
                return cached
            
            # Fetch from database
            logger.debug(f"Cache miss: {key}, fetching from database")
            result = await fetch_func()
            
            # Store in cache
            await self.redis.setex(key, ttl, str(result))
            
            return result
        except Exception as e:
            logger.error(f"Caching error: {e}")
            # Fallback to direct fetch
            return await fetch_func()
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache keys matching pattern"""
        keys = await self.redis.keys(pattern)
        if keys:
            return await self.redis.delete(*keys)
        return 0
    
    def get_cache_key(self, namespace: str, **kwargs) -> str:
        """Generate consistent cache key"""
        sorted_params = "_".join(
            f"{k}_{v}" for k, v in sorted(kwargs.items())
        )
        return f"cache:{namespace}:{sorted_params}"


class DatabaseConnectionPoolOptimizer:
    """Optimizes database connection pool settings"""
    
    # Recommended pool sizes based on concurrent users
    POOL_SIZE_RECOMMENDATIONS = {
        "development": {"pool_size": 5, "max_overflow": 10},
        "staging": {"pool_size": 20, "max_overflow": 30},
        "production": {"pool_size": 50, "max_overflow": 100},
    }
    
    @staticmethod
    def get_recommended_settings(environment: str, concurrent_users: int) -> Dict:
        """Get recommended pool settings for environment and user count"""
        base = DatabaseConnectionPoolOptimizer.POOL_SIZE_RECOMMENDATIONS.get(
            environment,
            DatabaseConnectionPoolOptimizer.POOL_SIZE_RECOMMENDATIONS["staging"]
        )
        
        # Adjust based on concurrent users
        multiplier = max(1, concurrent_users // 100)
        
        return {
            "pool_size": base["pool_size"] * multiplier,
            "max_overflow": base["max_overflow"] * multiplier,
            "pool_pre_ping": True,
            "pool_recycle": 3600,  # Recycle connections every hour
        }
    
    @staticmethod
    def get_diagnostics(engine) -> Dict:
        """Get connection pool diagnostics"""
        pool = engine.pool
        
        return {
            "pool_size": pool.pool_size if hasattr(pool, 'pool_size') else 'N/A',
            "max_overflow": pool.max_overflow if hasattr(pool, 'max_overflow') else 'N/A',
            "checkedout": pool.checkedout() if hasattr(pool, 'checkedout') else 'N/A',
            "checkedin": pool.size() - pool.checkedout() if hasattr(pool, 'checkedout') else 'N/A',
        }


# Caching strategies for common queries
CACHE_STRATEGIES = {
    "trending_memes": {
        "ttl": 300,  # 5 minutes
        "key": "trending:memes:{period}",
        "invalidate_on": ["meme_created", "meme_liked"],
    },
    "user_gallery": {
        "ttl": 600,  # 10 minutes
        "key": "user:gallery:{user_id}",
        "invalidate_on": ["meme_created", "meme_deleted"],
    },
    "templates": {
        "ttl": 86400,  # 24 hours
        "key": "templates:all",
        "invalidate_on": ["template_created", "template_updated"],
    },
    "user_profile": {
        "ttl": 1800,  # 30 minutes
        "key": "user:profile:{user_id}",
        "invalidate_on": ["user_updated"],
    },
}
