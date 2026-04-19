from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .routers import memes, jobs, trending, auth, stripe as stripe_router, users, health
from .db.session import engine, Base
from .core.config import settings
from .core.middleware import register_middleware
from .core.cors import setup_cors_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Cleanup on shutdown
    from .routers.health import cleanup_health_checker
    await cleanup_health_checker()


app = FastAPI(
    title="MemeGPT API",
    version="2.0.0",
    description="AI meme generation API powered by GPT-4o",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS & Security Middleware ──────────────────────────────────────────────
# Configure CORS for frontend communication with security best practices
setup_cors_middleware(app)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

register_middleware(app)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router,        prefix="/api",         tags=["health"])
app.include_router(auth.router,          prefix="/api/auth",    tags=["auth"])
app.include_router(memes.router,         prefix="/api/memes",   tags=["memes"])
app.include_router(jobs.router,          prefix="/api/jobs",    tags=["jobs"])
app.include_router(trending.router,      prefix="/api/trending",tags=["trending"])
app.include_router(stripe_router.router, prefix="/api/stripe",  tags=["billing"])
app.include_router(users.router,         prefix="/api/auth",    tags=["users"])

