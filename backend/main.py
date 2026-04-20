from contextlib import asynccontextmanager
import sys
import os

# Ensure backend directory is on Python path for uvicorn imports
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from routers import memes, jobs, trending, auth, stripe as stripe_router, users, health
from db.session import Base
from core.config import settings
from core.middleware import register_middleware
from core.cors import setup_cors_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database engine
    from db.session import _init_engine
    _init_engine()
    
    # Import engine after initialization
    from db.session import engine
    
    try:
        # Create tables on startup (use Alembic in production)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        # Log but don't fail startup if database isn't available
        print(f"⚠️  Warning: Could not initialize database tables: {e}")
        print("   Continuing without database - API docs will still be available")
    
    yield
    
    try:
        # Cleanup on shutdown
        from routers.health import cleanup_health_checker
        await cleanup_health_checker()
    except Exception as e:
        print(f"Warning during shutdown: {e}")


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

