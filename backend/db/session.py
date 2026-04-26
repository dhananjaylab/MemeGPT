from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


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
    
    engine = create_async_engine(
        settings.database_url,
        echo=False,  # Set to False in production
        future=True,
    )
    
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db() -> AsyncSession:
    """Get a database session for dependency injection."""
    if AsyncSessionLocal is None:
        _init_engine()
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()