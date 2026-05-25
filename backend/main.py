from contextlib import asynccontextmanager
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from routers import memes, jobs, trending, auth, stripe as stripe_router, users, health, ai, storage
from db.session import Base, get_db
from models.models import MemeTemplate
from core.config import settings
from core.middleware import register_middleware
from core.cors import setup_cors_middleware
from services.template_catalog import build_template_fields


# ── Template seeding ──────────────────────────────────────────────────────────

async def seed_templates_if_needed() -> None:
    """
    Seed and refresh curated meme templates on startup.
    """
    try:
        db_gen = get_db()
        db = await db_gen.__anext__()

        try:
            result = await db.execute(select(MemeTemplate))
            existing = result.scalars().all()

            meme_data_path = Path(__file__).parent / "public" / "meme_data.json"
            if not meme_data_path.exists():
                print("[WARNING] meme_data.json not found — skipping template seeding")
                return

            with open(meme_data_path, encoding="utf-8") as f:
                templates_data = json.load(f)

            existing_by_id = {t.id: t for t in existing}
            added = updated = 0

            for td in templates_data:
                tid = td["id"]
                fields = build_template_fields(td)
                current = existing_by_id.get(tid)

                if current:
                    for key, value in fields.items():
                        setattr(current, key, value)
                    updated += 1
                else:
                    db.add(MemeTemplate(id=tid, **fields))
                    added += 1

            await db.commit()
            print(f"[OK] Template catalog ready. Added {added}, updated {updated}.")
        finally:
            await db.close()

    except Exception as exc:
        print(f"[WARNING] Template seeding failed: {exc}")
        print("          Templates can be seeded via POST /api/memes/seed-templates")


# ── App lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB engine
    from db.session import _init_engine
    _init_engine()
    from db.session import engine

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await seed_templates_if_needed()
    except Exception as exc:
        print(f"[WARNING] DB init failed: {exc}")

    yield

    try:
        from routers.health import cleanup_health_checker
        await cleanup_health_checker()
    except Exception as exc:
        print(f"[WARNING] Shutdown cleanup error: {exc}")


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="MemeGPT API",
    version="2.1.0",
    description="AI meme generation API — Gen-Z edition powered by Google Gemini",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS + security middleware
setup_cors_middleware(app)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
register_middleware(app)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health.router,        prefix="/api",          tags=["health"])
app.include_router(auth.router,          prefix="/api/auth",     tags=["auth"])
app.include_router(memes.router,         prefix="/api/memes",    tags=["memes"])
app.include_router(jobs.router,          prefix="/api/jobs",     tags=["jobs"])
app.include_router(trending.router,      prefix="/api/trending", tags=["trending"])
app.include_router(ai.router,            prefix="/api/ai",       tags=["ai"])
app.include_router(stripe_router.router, prefix="/api/stripe",   tags=["billing"])
app.include_router(users.router,         prefix="/api/auth",     tags=["users"])
app.include_router(users.router,         prefix="/api/users",    tags=["users"])
app.include_router(storage.router,       prefix="/api/storage",  tags=["storage"])

# ── Static files ──────────────────────────────────────────────────────────────

_root = Path(__file__).parent

for _name, _path in [
    ("frames", _root / "public" / "frames"),
    ("fonts",  _root / "public" / "fonts"),
    ("output", _root / "public" / "output"),
    ("static", _root / "public"),
]:
    if _path.exists():
        app.mount(f"/{_name}", StaticFiles(directory=str(_path)), name=_name)
        print(f"[OK] Mounted /{_name} -> {_path}")
    else:
        print(f"[WARNING] Static dir not found: {_path}")
