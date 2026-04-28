from contextlib import asynccontextmanager
import sys
import os
import json
from pathlib import Path

# Ensure backend directory is on Python path for uvicorn imports
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy import select

from routers import memes, jobs, trending, auth, stripe as stripe_router, users, health, ai
from db.session import Base, get_db
from models.models import MemeTemplate
from core.config import settings
from core.middleware import register_middleware
from core.cors import setup_cors_middleware


async def seed_templates_if_needed():
    """Seed meme templates on startup if database is empty"""
    try:
        # Get database session
        db_gen = get_db()
        db = await db_gen.__anext__()
        
        try:
            # Check if templates already exist
            result = await db.execute(select(MemeTemplate))
            existing_templates = result.scalars().all()
            
            if len(existing_templates) > 0:
                print(f"[OK] Found {len(existing_templates)} existing templates in database")
                return
            
            print("[INFO] No templates found. Seeding templates from meme_data.json...")
            
            # Load meme data
            meme_data_path = Path(__file__).parent.parent / "public" / "meme_data.json"
            
            if not meme_data_path.exists():
                print(f"[WARNING] meme_data.json not found at {meme_data_path}")
                return
            
            with open(meme_data_path, 'r', encoding='utf-8') as f:
                templates_data = json.load(f)
            
            # Fallback image URLs using imgflip API through our proxy to avoid CORS
            fallback_images = {
                0: "https://i.imgflip.com/30b1gx.jpg",  # Drake
                1: "https://i.imgflip.com/1ur9b0.jpg",  # Distracted Boyfriend
                2: "https://i.imgflip.com/22bdq6.jpg",  # Left Exit
                3: "https://i.imgflip.com/26am.jpg",    # One Does Not Simply
                4: "https://i.imgflip.com/1bij.jpg",    # Success Kid
                5: "https://i.imgflip.com/1g8my4.jpg",  # Disaster Girl
                6: "https://i.imgflip.com/gk5el.jpg",   # Hide the Pain Harold
                7: "https://i.imgflip.com/1ihzfe.jpg",  # Surprised Pikachu
                8: "https://i.imgflip.com/261o3j.jpg",  # Change My Mind
                9: "https://i.imgflip.com/1c1uej.jpg",  # Leonardo Dicaprio Cheers
                10: "https://i.imgflip.com/1otk96.jpg", # Trump Bill Signing
            }
            
            added = 0
            frames_dir = Path(__file__).parent.parent / "public" / "frames"
            
            for template_data in templates_data:
                tid = template_data['id']
                
                # Priority 1: Use local file if it exists
                local_file_path = frames_dir / template_data['file_path']
                if local_file_path.exists():
                    # Use local static file URL (will be served by FastAPI StaticFiles)
                    image_url = f"/frames/{template_data['file_path']}"
                    preview_url = image_url
                    print(f"  [OK] Template {tid} ({template_data['name']}): Using local file")
                else:
                    # Priority 2: Use external URL with proxy as fallback
                    external_url = fallback_images.get(tid, "https://i.imgflip.com/30b1gx.jpg")
                    image_url = f"/api/memes/proxy-image?url={external_url}"
                    preview_url = image_url
                    print(f"  [WARNING] Template {tid} ({template_data['name']}): Local file not found, using proxy")
                
                template = MemeTemplate(
                    id=tid,
                    name=template_data['name'],
                    alternative_names=template_data.get('alternative_names', []),
                    file_path=template_data['file_path'],
                    font_path=template_data['font_path'],
                    text_color=template_data['text_color'],
                    text_stroke=template_data.get('text_stroke', False),
                    usage_instructions=template_data['usage_instructions'],
                    number_of_text_fields=template_data['number_of_text_fields'],
                    text_coordinates_xy_wh=template_data['text_coordinates_xy_wh'],
                    text_coordinates=template_data['text_coordinates_xy_wh'],
                    example_output=template_data['example_output'],
                    image_url=image_url,
                    preview_image_url=preview_url,
                    source="local"
                )
                db.add(template)
                added += 1
            
            await db.commit()
            print(f"[OK] Successfully seeded {added} templates into database")
            
        finally:
            await db.close()
            
    except Exception as e:
        print(f"[WARNING] Could not seed templates: {e}")
        print("   Templates can be seeded manually via /api/memes/seed-templates endpoint")


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
        
        # Seed templates if database is empty
        await seed_templates_if_needed()
        
    except Exception as e:
        # Log but don't fail startup if database isn't available
        print(f"[WARNING] Could not initialize database tables: {e}")
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
app.include_router(ai.router,            prefix="/api/ai",      tags=["ai"])
app.include_router(stripe_router.router, prefix="/api/stripe",  tags=["billing"])
app.include_router(users.router,         prefix="/api/auth",    tags=["users"])
app.include_router(users.router,         prefix="/api/users",   tags=["users"])

# ── Static Files ──────────────────────────────────────────────────────────────
# Mount static files for serving template images, fonts, and generated memes
# IMPORTANT: These must be mounted AFTER all API routes to avoid conflicts

# Serve template images from public/frames directory
frames_path = Path(__file__).parent.parent / "public" / "frames"
if frames_path.exists():
    app.mount("/frames", StaticFiles(directory=str(frames_path)), name="frames")
    print(f"[OK] Mounted /frames -> {frames_path}")
else:
    print(f"[WARNING] Frames directory not found at {frames_path}")

# Serve fonts from public/fonts directory
fonts_path = Path(__file__).parent.parent / "public" / "fonts"
if fonts_path.exists():
    app.mount("/fonts", StaticFiles(directory=str(fonts_path)), name="fonts")
    print(f"[OK] Mounted /fonts -> {fonts_path}")
else:
    print(f"[WARNING] Fonts directory not found at {fonts_path}")

# Serve other static assets
public_path = Path(__file__).parent.parent / "public"
if public_path.exists():
    app.mount("/static", StaticFiles(directory=str(public_path)), name="static")
    print(f"[OK] Mounted /static -> {public_path}")

# Made with Bob
 
 2 8   A p r i l   2 0 2 6   2 3 : 0 4 : 4 6  
  
  
 