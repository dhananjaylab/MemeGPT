from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from db.session import get_db
from models.models import GeneratedMeme, User, MemeTemplate
from services.auth import get_current_user_optional
from services.rate_limit import rate_limit_request
from workers.meme_worker import process_meme_generation
from services.worker import enqueue_meme_generation
from services.imgflip import imgflip_service

import json
from pathlib import Path
import httpx
router = APIRouter()


class GenerateMemeRequest(BaseModel):
    prompt: str
    ai_provider: Optional[str] = "openai"  # "openai" or "gemini"
    generation_mode: Optional[str] = "auto"  # "auto" or "manual"
    template_id: Optional[int] = None
    captions: Optional[List[str]] = None


class GenerateMemeResponse(BaseModel):
    job_id: str
    remaining_generations: int


class MemeResponse(BaseModel):
    id: str
    template_name: str
    template_id: int
    meme_text: List[str]
    image_url: str
    created_at: str
    share_count: int
    like_count: int


class TemplateResponse(BaseModel):
    id: int
    name: str
    image_url: Optional[str]
    text_field_count: int
    text_coordinates: List[List[int]]
    preview_image_url: Optional[str]
    font_path: str
    usage_instructions: Optional[str] = None
    source: Optional[str] = "local"  # "local" or "imgflip"
    imgflip_id: Optional[str] = None


@router.post("/generate", response_model=GenerateMemeResponse)
async def generate_meme(
    request: Request,
    body: GenerateMemeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Generate memes from user prompt (async with job queue)"""
    
    # Rate limit check is now handled by middleware
    remaining = getattr(request.state, "rate_limit_remaining", 0)
    
    # Validate prompt
    if not body.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    
    if len(body.prompt) > 1000:
        raise HTTPException(status_code=400, detail="Prompt too long (max 1000 characters)")
    
    # Normalize ai_provider
    ai_provider = (body.ai_provider or "openai").lower()
    if ai_provider not in {"openai", "gemini"}:
        raise HTTPException(status_code=400, detail="ai_provider must be 'openai' or 'gemini'")

    # Normalize generation mode
    generation_mode = (body.generation_mode or "auto").lower()
    if generation_mode not in {"auto", "manual"}:
        raise HTTPException(status_code=400, detail="generation_mode must be 'auto' or 'manual'")

    if generation_mode == "manual":
        if body.template_id is None:
            raise HTTPException(status_code=400, detail="template_id is required for manual mode")
        if not body.captions or not any(c.strip() for c in body.captions):
            raise HTTPException(status_code=400, detail="captions are required for manual mode")
    
    # Enqueue meme generation job with specified AI provider
    job_id = await enqueue_meme_generation(
        prompt=body.prompt,
        user=current_user,
        ai_provider=ai_provider,
        generation_mode=generation_mode,
        manual_template_id=body.template_id,
        manual_captions=body.captions,
    )
    
    return GenerateMemeResponse(
        job_id=job_id,
        remaining_generations=remaining
    )


@router.get("", response_model=List[MemeResponse])
async def get_memes_alias(
    page: int = 1,
    limit: int = 20,
    sort: str = "recent",
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Alias for /public endpoint - Get public memes for gallery"""
    return await get_public_memes(page, limit, sort, search, db)


@router.get("/public", response_model=List[MemeResponse])
async def get_public_memes(
    page: int = 1,
    limit: int = 20,
    sort: str = "recent",  # "recent", "top", "trending"
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get public memes for gallery"""
    
    # Validate pagination
    if page < 1:
        page = 1
    if limit > 100:
        limit = 100
    
    offset = (page - 1) * limit
    
    # Build query
    query = select(GeneratedMeme).where(GeneratedMeme.is_public == True)
    
    # Add search filter
    if search:
        search_term = f"%{search}%"
        query = query.where(
            GeneratedMeme.prompt.ilike(search_term) |
            GeneratedMeme.template_name.ilike(search_term)
        )
    
    # Add sorting
    if sort == "top":
        query = query.order_by(desc(GeneratedMeme.share_count))
    elif sort == "trending":
        # Simple trending: high share count + recent
        query = query.order_by(
            desc(GeneratedMeme.share_count * 0.7 + GeneratedMeme.created_at.timestamp() * 0.3)
        )
    else:  # recent
        query = query.order_by(desc(GeneratedMeme.created_at))
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    memes = result.scalars().all()
    
    return [
        MemeResponse(
            id=meme.id,
            template_name=meme.template_name,
            template_id=meme.template_id,
            meme_text=meme.meme_text,
            image_url=meme.image_url,
            created_at=meme.created_at.isoformat(),
            share_count=meme.share_count,
            like_count=meme.like_count
        )
        for meme in memes
    ]


@router.get("/my", response_model=List[MemeResponse])
async def get_my_memes(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get current user's memes"""
    
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Validate pagination
    if page < 1:
        page = 1
    if limit > 100:
        limit = 100
    
    offset = (page - 1) * limit
    
    # Get user's memes
    query = (
        select(GeneratedMeme)
        .where(GeneratedMeme.user_id == current_user.id)
        .order_by(desc(GeneratedMeme.created_at))
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    memes = result.scalars().all()
    
    return [
        MemeResponse(
            id=meme.id,
            template_name=meme.template_name,
            template_id=meme.template_id,
            meme_text=meme.meme_text,
            image_url=meme.image_url,
            created_at=meme.created_at.isoformat(),
            share_count=meme.share_count,
            like_count=meme.like_count
        )
        for meme in memes
    ]


# Template Management Endpoints
# NOTE: These must come BEFORE /{meme_id} route to avoid path conflicts

@router.get("/templates", response_model=List[TemplateResponse])
async def get_templates(
    source: Optional[str] = None,  # "all", "local", or "imgflip"
    db: AsyncSession = Depends(get_db)
):
    """Get all available meme templates for AI suggestions and manual editor"""
    
    # Build query with optional source filter
    query = select(MemeTemplate)
    if source and source != "all":
        query = query.where(MemeTemplate.source == source)
    
    result = await db.execute(query)
    templates = result.scalars().all()
    
    return [
        TemplateResponse(
            id=template.id,
            name=template.name,
            image_url=template.image_url,
            text_field_count=template.number_of_text_fields,
            text_coordinates=template.text_coordinates or template.text_coordinates_xy_wh,
            preview_image_url=template.preview_image_url or template.image_url,
            font_path=template.font_path,
            usage_instructions=template.usage_instructions,
            source=template.source,
            imgflip_id=template.imgflip_id,
        )
        for template in templates
    ]


@router.post("/templates/sync-imgflip")
async def sync_imgflip_templates(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Sync popular meme templates from Imgflip API to database.
    This endpoint fetches the top 100 templates and caches them.
    """
    try:
        # Perform sync
        stats = await imgflip_service.sync_templates_to_db(db)
        
        return {
            "success": True,
            "message": f"Successfully synced Imgflip templates",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync Imgflip templates: {str(e)}"
        )


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get specific meme template details"""
    
    result = await db.execute(select(MemeTemplate).where(MemeTemplate.id == template_id))
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return TemplateResponse(
        id=template.id,
        name=template.name,
        image_url=template.image_url,
        text_field_count=template.number_of_text_fields,
        text_coordinates=template.text_coordinates or template.text_coordinates_xy_wh,
        preview_image_url=template.preview_image_url or template.image_url,
        font_path=template.font_path,
        usage_instructions=template.usage_instructions,
        source=template.source,
        imgflip_id=template.imgflip_id,
    )


@router.get("/{meme_id}", response_model=MemeResponse)
async def get_meme(
    meme_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get specific meme by ID"""
    
    result = await db.execute(select(GeneratedMeme).where(GeneratedMeme.id == meme_id))
    meme = result.scalar_one_or_none()
    
    if not meme:
        raise HTTPException(status_code=404, detail="Meme not found")
    
    if not meme.is_public:
        raise HTTPException(status_code=404, detail="Meme not found")
    
    return MemeResponse(
        id=meme.id,
        template_name=meme.template_name,
        template_id=meme.template_id,
        meme_text=meme.meme_text,
        image_url=meme.image_url,
        created_at=meme.created_at.isoformat(),
        share_count=meme.share_count,
        like_count=meme.like_count
    )


@router.post("/{meme_id}/share")
async def share_meme(
    meme_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Increment share count for a meme"""
    
    result = await db.execute(select(GeneratedMeme).where(GeneratedMeme.id == meme_id))
    meme = result.scalar_one_or_none()
    
    if not meme:
        raise HTTPException(status_code=404, detail="Meme not found")
    
    if not meme.is_public:
        raise HTTPException(status_code=404, detail="Meme not found")
    
    # Increment share count
    meme.share_count += 1
    await db.commit()
    
    return {"message": "Share count updated", "share_count": meme.share_count}


@router.post("/{meme_id}/like")
async def like_meme(
    meme_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Increment like count for a meme"""
    
    result = await db.execute(select(GeneratedMeme).where(GeneratedMeme.id == meme_id))
    meme = result.scalar_one_or_none()
    
    if not meme:
        raise HTTPException(status_code=404, detail="Meme not found")
    
    # Increment like count
    meme.like_count += 1
    await db.commit()
    
    return {"message": "Liked", "liked": True, "like_count": meme.like_count}


@router.delete("/{meme_id}")
async def delete_meme(
    meme_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Delete a meme (only by owner)"""
    
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    result = await db.execute(select(GeneratedMeme).where(GeneratedMeme.id == meme_id))
    meme = result.scalar_one_or_none()
    
    if not meme:
        raise HTTPException(status_code=404, detail="Meme not found")
    
    if meme.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this meme")
    
    await db.delete(meme)
    await db.commit()


@router.post("/seed-templates")
async def seed_templates(db: AsyncSession = Depends(get_db)):
    """Seed meme templates from meme_data.json with fallback images"""
    
    # Load meme data
    meme_data_path = Path(__file__).parent.parent.parent / "public" / "meme_data.json"
    
    if not meme_data_path.exists():
        raise HTTPException(status_code=500, detail="meme_data.json not found")
    
    with open(meme_data_path, 'r', encoding='utf-8') as f:
        templates_data = json.load(f)
    
    # Fallback image URLs using imgflip API
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
    updated = 0
    
    for template_data in templates_data:
        tid = template_data['id']
        
        # Check if exists
        result = await db.execute(
            select(MemeTemplate).where(MemeTemplate.id == tid)
        )
        existing = result.scalar_one_or_none()
        
        # Use fallback image
        image_url = fallback_images.get(tid, f"https://i.imgflip.com/30b1gx.jpg")
        
        if existing:
            # Update
            existing.name = template_data['name']
            existing.alternative_names = template_data.get('alternative_names', [])
            existing.file_path = template_data['file_path']
            existing.font_path = template_data['font_path']
            existing.text_color = template_data['text_color']
            existing.text_stroke = template_data.get('text_stroke', False)
            existing.usage_instructions = template_data['usage_instructions']
            existing.number_of_text_fields = template_data['number_of_text_fields']
            existing.text_coordinates_xy_wh = template_data['text_coordinates_xy_wh']
            existing.text_coordinates = template_data['text_coordinates_xy_wh']
            existing.example_output = template_data['example_output']
            existing.image_url = image_url
            existing.preview_image_url = image_url
            updated += 1
        else:
            # Create
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
                preview_image_url=image_url
            )
            db.add(template)
            added += 1
    
    await db.commit()
    
    return {
        "message": "Templates seeded successfully",
        "added": added,
        "updated": updated,
        "total": added + updated
    }
    
    return {"message": "Meme deleted successfully"}


@router.get("/proxy-image")
async def proxy_template_image(url: str):
    """Proxy external template images to avoid CORS issues"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            
            # Return image with proper headers
            return Response(
                content=response.content,
                media_type=response.headers.get("content-type", "image/jpeg"),
                headers={
                    "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
                    "Access-Control-Allow-Origin": "*",
                }
            )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to fetch image: {str(e)}")