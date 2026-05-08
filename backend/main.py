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

from routers import memes, jobs, trending, auth, stripe as stripe_router, users, health, ai
from db.session import Base, get_db
from models.models import MemeTemplate
from core.config import settings
from core.middleware import register_middleware
from core.cors import setup_cors_middleware


# ── Template seeding ──────────────────────────────────────────────────────────

async def seed_templates_if_needed() -> None:
    """
    Seed meme templates on startup if the DB has fewer templates than meme_data.json.
    Supports all 26 templates (11 classic + 15 Gen-Z) with fallback_url field.
    """
    try:
        db_gen = get_db()
        db = await db_gen.__anext__()

        try:
            result = await db.execute(select(MemeTemplate))
            existing = result.scalars().all()

            meme_data_path = Path(__file__).parent.parent / "public" / "meme_data.json"
            if not meme_data_path.exists():
                print("[WARNING] meme_data.json not found — skipping template seeding")
                return

            with open(meme_data_path, encoding="utf-8") as f:
                templates_data = json.load(f)

            existing_ids = {t.id for t in existing}
            missing = [t for t in templates_data if t["id"] not in existing_ids]

            if not missing:
                print(f"[OK] {len(existing)} templates already in database (no seeding needed)")
                return

            print(f"[INFO] Seeding {len(missing)} new templates...")

            frames_dir = Path(__file__).parent.parent / "public" / "frames"
            added = 0

            for td in missing:
                tid = td["id"]
                local_file = frames_dir / td["file_path"]

                if local_file.exists():
                    image_url = f"/frames/{td['file_path']}"
                elif td.get("fallback_url"):
                    image_url = f"/api/memes/proxy-image?url={td['fallback_url']}"
                else:
                    image_url = None

                db.add(MemeTemplate(
                    id=tid,
                    name=td["name"],
                    alternative_names=td.get("alternative_names", []),
                    file_path=td["file_path"],
                    font_path=td["font_path"],
                    text_color=td["text_color"],
                    text_stroke=td.get("text_stroke", True),
                    usage_instructions=td["usage_instructions"],
                    number_of_text_fields=td["number_of_text_fields"],
                    text_coordinates_xy_wh=td["text_coordinates_xy_wh"],
                    text_coordinates=td["text_coordinates_xy_wh"],
                    example_output=td["example_output"],
                    image_url=image_url,
                    preview_image_url=image_url,
                    fallback_url=td.get("fallback_url"),
                    source="local",
                    gen_z_ready=True,  # all curated templates are Gen-Z ready
                ))
                added += 1

            await db.commit()
            print(f"[OK] Seeded {added} templates. Total in DB: {len(existing) + added}")

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
    description="AI meme generation API — Gen-Z edition powered by GPT-4o & Gemini",
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

# ── Static files ──────────────────────────────────────────────────────────────

_root = Path(__file__).parent.parent

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
