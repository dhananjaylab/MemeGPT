from contextlib import asynccontextmanager
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

# Phase 2: logging + Sentry must be configured before the FastAPI app (and
# anything that might log during import) is constructed — previously
# neither was ever wired up despite both being declared dependencies and
# SENTRY_DSN being set in every .env* file.
from core.logging import configure_logging, get_logger
from core.sentry import init_sentry

configure_logging()
init_sentry()

logger = get_logger(__name__)

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
                logger.warning("meme_data_json_missing", path=str(meme_data_path))
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
            logger.info("template_catalog_ready", added=added, updated=updated)
        finally:
            await db.close()

    except Exception as exc:
        logger.error("template_seeding_failed", error=str(exc))
        logger.info("templates_can_be_seeded_via", endpoint="POST /api/v1/memes/seed-templates (admin-only)")


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
        logger.error("db_init_failed", error=str(exc))

    yield

    try:
        from routers.health import cleanup_health_checker
        await cleanup_health_checker()
    except Exception as exc:
        logger.error("shutdown_cleanup_error", error=str(exc))


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="MemeGPT API",
    version="2.2.0",
    description="AI meme generation API — Gen-Z edition powered by Google Gemini, with Anthropic fallback",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS + security middleware
setup_cors_middleware(app)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
register_middleware(app)

# ── Routers ───────────────────────────────────────────────────────────────────
#
# Phase 2: introduced /api/v1 as the canonical, documented API surface.
# Every router is ALSO still mounted under the legacy unversioned /api
# prefix (include_in_schema=False so it doesn't clutter /docs) — existing
# API-plan integrations hitting /api/... directly keep working unchanged.
# core.middleware.DeprecatedApiAliasMiddleware tags those legacy responses
# with Deprecation/Link headers pointing at the /api/v1 successor. The
# frontend (frontend/src/lib/api.ts) has already been switched to call
# /api/v1 directly.

API_V1_PREFIX = "/api/v1"
API_LEGACY_PREFIX = "/api"


def _mount_routers(prefix: str, include_in_schema: bool) -> None:
    app.include_router(health.router,        prefix=f"{prefix}",          tags=["health"],   include_in_schema=include_in_schema)
    app.include_router(auth.router,          prefix=f"{prefix}/auth",     tags=["auth"],     include_in_schema=include_in_schema)
    app.include_router(memes.router,         prefix=f"{prefix}/memes",    tags=["memes"],    include_in_schema=include_in_schema)
    app.include_router(jobs.router,          prefix=f"{prefix}/jobs",     tags=["jobs"],     include_in_schema=include_in_schema)
    app.include_router(trending.router,      prefix=f"{prefix}/trending", tags=["trending"], include_in_schema=include_in_schema)
    app.include_router(ai.router,            prefix=f"{prefix}/ai",       tags=["ai"],       include_in_schema=include_in_schema)
    app.include_router(stripe_router.router, prefix=f"{prefix}/stripe",   tags=["billing"],  include_in_schema=include_in_schema)
    app.include_router(users.router,         prefix=f"{prefix}/auth",     tags=["users"],    include_in_schema=include_in_schema)
    app.include_router(users.router,         prefix=f"{prefix}/users",    tags=["users"],    include_in_schema=include_in_schema)
    app.include_router(storage.router,       prefix=f"{prefix}/storage",  tags=["storage"],  include_in_schema=include_in_schema)


_mount_routers(API_V1_PREFIX, include_in_schema=True)
_mount_routers(API_LEGACY_PREFIX, include_in_schema=False)

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
        logger.info("static_mounted", route=f"/{_name}", path=str(_path))
    else:
        logger.warning("static_dir_not_found", path=str(_path))
