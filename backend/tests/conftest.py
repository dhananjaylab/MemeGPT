"""
Shared pytest fixtures for the MemeGPT test suite.

Design philosophy:
  - Every fixture that touches a database uses an async SQLite in-memory DB
    via SQLAlchemy's aiosqlite dialect — no real Postgres needed in CI.
  - Redis-dependent code is patched with AsyncMock at the service level,
    never connecting to a real Redis.
  - FastAPI app is built fresh per-session using the same lifespan mechanism
    as production, but with the DB/Redis overrides applied first.
  - Fixtures are layered: db_session → auth_headers → admin_auth_headers,
    so each test only requests what it actually needs.
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# ── force test-safe settings before any module is fully loaded ───────────────
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-32x")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ.setdefault("ANTHROPIC_API_KEY", "")
os.environ.setdefault("MODERATION_ENABLED", "false")
os.environ.setdefault("GENERATION_BURST_LIMIT", "5")

# ── make the backend package importable ──────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.config import settings
from db.session import Base, get_db
from models.models import GeneratedMeme, MemeJob, MemeTemplate, User
from services.auth import create_access_token, REFRESH_COOKIE_NAME


# ── In-memory SQLite engine (shared across the session) ──────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

_test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
_TestSessionLocal = async_sessionmaker(
    _test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session", autouse=True)
def event_loop_policy():
    """Use the default asyncio event loop policy for all tests."""
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

@pytest.fixture(scope="session")
def event_loop():
    """Provide a session-scoped loop so session async fixtures can initialize."""
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


@pytest_asyncio.fixture(scope="session")
async def create_tables():
    """Create all ORM tables once per session in the in-memory SQLite DB."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(create_tables) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a clean AsyncSession per test.

    Each test runs inside a SAVEPOINT (nested transaction) that is rolled
    back at the end — no test data bleeds into the next test and there is
    no need to truncate tables between runs.
    """
    async with _TestSessionLocal() as session:
        await session.begin_nested()  # SAVEPOINT
        try:
            yield session
        finally:
            await session.rollback()  # roll back to SAVEPOINT


@pytest_asyncio.fixture
async def app(db_session: AsyncSession) -> FastAPI:
    """
    Build a minimal FastAPI app with DB and Redis overrides applied.

    Rather than importing main.py (which triggers heavy side-effects like
    Sentry init and template seeding), we build a focused app that mounts
    only the routers under test and overrides get_db with our in-memory
    session — the same contract as the real app but without the noise.
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    # Lazy imports — avoids importing the actual router modules before the
    # DB override is in place, which would trigger SQLAlchemy engine creation.
    from routers.memes import router as memes_router
    from routers.auth import router as auth_router
    from routers.health import router as health_router

    _app = FastAPI()
    _app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    async def _override_get_db():
        yield db_session

    _app.dependency_overrides[get_db] = _override_get_db

    _app.include_router(auth_router, prefix="/api/v1/auth")
    _app.include_router(memes_router, prefix="/api/v1/memes")
    _app.include_router(health_router, prefix="")

    return _app


@pytest_asyncio.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient wired to the test app — use for async test functions."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


# ── User factories ────────────────────────────────────────────────────────────

def _make_user(
    *,
    plan: str = "free",
    is_admin: bool = False,
    daily_limit: int = 5,
    daily_used: int = 0,
    email: str | None = None,
) -> User:
    uid = str(uuid4())
    return User(
        id=uid,
        email=email or f"user_{uid[:8]}@test.example",
        plan=plan,
        daily_limit=daily_limit,
        daily_used=daily_used,
        is_admin=is_admin,
        preferences={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest_asyncio.fixture
async def free_user(db_session: AsyncSession) -> User:
    user = _make_user(plan="free")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def pro_user(db_session: AsyncSession) -> User:
    user = _make_user(plan="pro", daily_limit=500)
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = _make_user(plan="pro", is_admin=True, daily_limit=500)
    db_session.add(user)
    await db_session.flush()
    return user


# ── Token / header helpers ────────────────────────────────────────────────────

def _bearer(user: User) -> dict:
    token = create_access_token({"sub": user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def free_user_headers(free_user: User) -> dict:
    return _bearer(free_user)


@pytest.fixture
def pro_user_headers(pro_user: User) -> dict:
    return _bearer(pro_user)


@pytest.fixture
def admin_headers(admin_user: User) -> dict:
    return _bearer(admin_user)


# ── Meme/template factories ───────────────────────────────────────────────────

def make_template(
    *,
    id: int = 0,
    name: str = "Drake Hotline Bling Meme",
    source: str = "local",
    n_fields: int = 2,
) -> MemeTemplate:
    return MemeTemplate(
        id=id,
        name=name,
        alternative_names=[],
        file_path="Drake-Hotline-Bling.jpg",
        font_path="impact.ttf",
        text_color="white",
        text_stroke=True,
        usage_instructions="Test usage instructions.",
        number_of_text_fields=n_fields,
        text_coordinates_xy_wh=[[0, 0, 100, 100]] * n_fields,
        text_coordinates=[[0, 0, 100, 100]] * n_fields,
        example_output=["text1", "text2"][:n_fields],
        source=source,
        gen_z_ready=True,
    )


def make_meme(
    *,
    user_id: str | None = None,
    is_public: bool = True,
    moderation_status: str = "approved",
    template_name: str = "Drake Hotline Bling Meme",
    template_id: int = 0,
) -> GeneratedMeme:
    return GeneratedMeme(
        id=str(uuid4()),
        user_id=user_id,
        prompt="test prompt",
        template_name=template_name,
        template_id=template_id,
        meme_text=["top text", "bottom text"],
        image_url="https://example.com/test.webp",
        is_public=is_public,
        moderation_status=moderation_status,
        share_count=0,
        like_count=0,
        trending_score=0.0,
        created_at=datetime.now(timezone.utc),
    )


# ── Redis mock (session-scoped — avoids repeated patching boilerplate) ────────

@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    """
    Patch every Redis call at the service layer so tests never need a live
    Redis. Applies to every test automatically (autouse=True).

    Tests that want to inspect specific Redis calls can request this fixture
    by name and interrogate the mock.
    """
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.exists = AsyncMock(return_value=0)
    redis_mock.eval = AsyncMock(return_value=[1, 4])  # count=1, remaining=4
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.info = AsyncMock(return_value={"redis_version": "7.0", "connected_clients": 1, "used_memory_human": "1M", "keyspace_hits": 0, "keyspace_misses": 0})
    redis_mock.publish = AsyncMock(return_value=1)
    redis_mock.keys = AsyncMock(return_value=[])
    redis_mock.zadd = AsyncMock(return_value=1)
    redis_mock.zrevrange = AsyncMock(return_value=[])
    redis_mock.zrem = AsyncMock(return_value=1)
    redis_mock.zremrangebyrank = AsyncMock(return_value=0)
    redis_mock.zcard = AsyncMock(return_value=0)

    async def _fake_from_url(*a, **kw):
        return redis_mock

    monkeypatch.setattr("services.rate_limit._redis", redis_mock)

    try:
        import services.cache as cache_mod
        monkeypatch.setattr(cache_mod, "_redis", redis_mock)
    except ImportError:
        pass

    try:
        import services.trending as trending_mod
        monkeypatch.setattr(trending_mod, "_redis", redis_mock)
    except ImportError:
        pass

    return redis_mock
