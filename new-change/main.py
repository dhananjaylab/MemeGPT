from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .routers import memes, jobs, trending, auth, stripe as stripe_router, users
from .db.session import engine, Base
from .core.config import settings
from .core.middleware import register_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="MemeGPT API",
    version="2.0.0",
    description="AI meme generation API powered by GPT-4o",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# Explicit origin list — never use "*" in production
ALLOWED_ORIGINS = [
    settings.frontend_url,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

register_middleware(app)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,          prefix="/api/auth",    tags=["auth"])
app.include_router(memes.router,         prefix="/api/memes",   tags=["memes"])
app.include_router(jobs.router,          prefix="/api/jobs",    tags=["jobs"])
app.include_router(trending.router,      prefix="/api/trending",tags=["trending"])
app.include_router(stripe_router.router, prefix="/api/stripe",  tags=["billing"])
app.include_router(users.router,         prefix="/api/auth",    tags=["users"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": app.version}
