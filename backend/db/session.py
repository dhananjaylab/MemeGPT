from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool
import logging

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass


# Lazy initialization - imported only when needed
engine = None
AsyncSessionLocal = None


def _init_engine():
    """Initialize the database engine. Called once at app startup."""
    global engine, AsyncSessionLocal
    if engine is not None:
        return
    
    from core.config import settings
    
    # For remote databases (like Neon), use QueuePool with proper configuration
    # This prevents "connection is closed" errors from stale connections
    engine = create_async_engine(
        settings.database_url,
        echo=False,  # Set to False in production
        future=True,
        # Connection pool settings for remote databases
        pool_size=5,  # Number of connections to keep in the pool
        max_overflow=10,  # Additional connections beyond pool_size
        pool_recycle=3600,  # Recycle connections after 1 hour (prevents stale connections)
        pool_pre_ping=True,  # Test connection before using (detects dead connections)
        connect_args={
            "server_settings": {"jit": "off"},  # Disable JIT for Neon compatibility
            "timeout": 10,  # Connection timeout in seconds
        }
    )
    
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    logger.info("Database engine initialized with connection pooling")


async def get_db() -> AsyncSession:
    """Get a database session for dependency injection."""
    if AsyncSessionLocal is None:
        _init_engine()
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            await session.close()