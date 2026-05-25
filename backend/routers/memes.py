"""
/api/memes — meme CRUD + generation endpoints.

v2 additions:
  • POST /generate/quick — synchronous fast-path (no queue, cache-first)
  • GET  /templates — now filters by source, returns Gen-Z-ready template list
  • POST /templates/sync-imgflip — unchanged
  • GET  /proxy-image — unchanged
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.models import GeneratedMeme, MemeTemplate, User
from services.auth import get_current_user_optional
from services.cache import (
    get_cached_meme_url,
    get_cached_captions,
    set_cached_captions,
    set_cached_meme_url,
    get_cached_meme_metadata,
    set_cached_meme_metadata,
)
from services.compositor import overlay_text_on_image_async
from services.imgflip import imgflip_service
from services.meme_ai import get_caption_generator
from services.storage import upload_to_r2
from services.template_catalog import build_template_fields
from services.trending import (
    compute_trending_score,
    get_trending_meme_ids,
    remove_from_trending,
    update_trending_score,
)
from services.worker import enqueue_meme_generation

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────────────

class GenerateMemeRequest(BaseModel):
    prompt: str
    ai_provider: Optional[str] = "openai"
    generation_mode: Optional[str] = "auto"
    template_id: Optional[int] = None
    captions: Optional[List[str]] = None


class GenerateMemeResponse(BaseModel):
    job_id: str
    remaining_generations: int


class QuickMemeRequest(BaseModel):
    """
    Fast synchronous generation — no queue, returns the meme URL directly.

    Two modes:
      • manual: provide template_id + captions
      • auto:   provide prompt only (one best template chosen by AI, cached)
    """
    prompt: Optional[str] = None
    template_id: Optional[int] = None
    captions: Optional[List[str]] = None
    ai_provider: Optional[str] = "openai"


class QuickMemeResponse(BaseModel):
    meme_id: str
    image_url: str
    template_name: str
    meme_text: List[str]
    cache_hit: bool
    generation_time_ms: int


class MemeResponse(BaseModel):
    id: str
    template_name: str
    template_id: int
    prompt: str
    meme_text: List[str]
    image_url: str
    created_at: str
    share_count: int
    like_count: int
    is_public: bool


class MemeListResponse(BaseModel):
    memes: List[MemeResponse]
    total: int
    page: int
    limit: int
    has_more: bool


class TemplateResponse(BaseModel):
    id: int
    name: str
    image_url: Optional[str]
    text_field_count: int
    text_coordinates: List[List[int]]
    preview_image_url: Optional[str]
    font_path: str
    usage_instructions: Optional[str] = None
    source: Optional[str] = "local"
    imgflip_id: Optional[str] = None


# ── Async generation helper (shared by quick + worker) ───────────────────────

async def _compose_and_upload(
    template_dict: dict,
    texts: List[str],
    prompt: str,
    user_id: Optional[str],
    db: AsyncSession,
) -> GeneratedMeme:
    """Compose image, upload to storage, persist to DB, return model instance."""
    
    # Check if this is an Imgflip template
    if template_dict.get("source") == "imgflip" and template_dict.get("imgflip_id"):
        logger.info(
            "Using Imgflip API for template %d (imgflip_id=%s)",
            template_dict["id"], template_dict["imgflip_id"]
        )
        try:
            # Use Imgflip caption API
            imgflip_result = await imgflip_service.caption_image(
                template_dict["imgflip_id"],
                texts
            )
            image_url = imgflip_result.get("data", {}).get("url")
            if not image_url:
                raise RuntimeError("Imgflip API did not return image URL")
            
            logger.info("Imgflip API generated meme: %s", image_url[:100])
        except Exception as imgflip_exc:
            logger.error(
                "Imgflip API failed for template %d: %s. Falling back to compositor.",
                template_dict["id"], imgflip_exc
            )
            # Fallback to local compositor
            image_buffer = await overlay_text_on_image_async(template_dict, texts)
            object_key = f"memes/{uuid4()}.webp"
            upload_result = await upload_to_r2(image_buffer, object_key)
            image_url = upload_result.get("primary") if isinstance(upload_result, dict) else None
            
            if not image_url:
                raise HTTPException(status_code=503, detail="Storage service unavailable: Cloudflare R2 unreachable")
    else:
        # Use local compositor for non-Imgflip templates
        image_buffer = await overlay_text_on_image_async(template_dict, texts)

        object_key = f"memes/{uuid4()}.webp"
        upload_result = await upload_to_r2(image_buffer, object_key)
        image_url = upload_result.get("primary") if isinstance(upload_result, dict) else None

        if not image_url:
            raise HTTPException(status_code=503, detail="Storage service unavailable: Cloudflare R2 unreachable")

    meme = GeneratedMeme(
        id=str(uuid4()),
        user_id=user_id,
        prompt=prompt or "quick-generate",
        template_name=template_dict["name"],
        template_id=template_dict["id"],
        meme_text=texts,
        image_url=image_url,
        is_public=True,
    )
    db.add(meme)
    await db.commit()
    
    # Cache the metadata to eliminate DB queries on future cache hits
    meme_metadata = {
        "meme_id": meme.id,
        "template_name": meme.template_name,
        "image_url": image_url,
    }
    await set_cached_meme_metadata(template_dict["id"], texts, meme_metadata)
    await set_cached_meme_url(template_dict["id"], texts, image_url)
    
    return meme


# ── /generate (async queue path) ─────────────────────────────────────────────

@router.post("/generate", response_model=GenerateMemeResponse)
async def generate_meme(
    request: Request,
    body: GenerateMemeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    remaining = getattr(request.state, "rate_limit_remaining", 0)

    if not body.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    if len(body.prompt) > 1000:
        raise HTTPException(status_code=400, detail="Prompt too long (max 1000 characters)")

    ai_provider = (body.ai_provider or "gemini").lower()
    if ai_provider not in {"gemini"}:
        raise HTTPException(status_code=400, detail="ai_provider must be 'gemini'")

    generation_mode = (body.generation_mode or "auto").lower()
    if generation_mode not in {"auto", "manual"}:
        raise HTTPException(status_code=400, detail="generation_mode must be 'auto' or 'manual'")

    if generation_mode == "manual":
        if body.template_id is None:
            raise HTTPException(status_code=400, detail="template_id required for manual mode")
        if not body.captions or not any(c.strip() for c in body.captions):
            raise HTTPException(status_code=400, detail="captions required for manual mode")

    job_id = await enqueue_meme_generation(
        prompt=body.prompt,
        user=current_user,
        ai_provider=ai_provider,
        generation_mode=generation_mode,
        manual_template_id=body.template_id,
        manual_captions=body.captions,
    )

    return GenerateMemeResponse(job_id=job_id, remaining_generations=remaining)


# ── /generate/quick (synchronous fast-path) ───────────────────────────────────

@router.post("/generate/quick")
async def generate_meme_quick(
    body: QuickMemeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Fast meme generation — returns the image URL directly if cached (<10ms),
    otherwise offloads to ARQ worker and returns 202 Accepted with job_id for SSE streaming.
    """
    t0 = time.monotonic()

    # ── 1. Check if we can serve instantly from cache ────────────────────────
    if body.template_id is not None and body.captions:
        # Manual mode
        template_id = body.template_id
        texts = [c.strip() for c in body.captions]
        prompt = body.prompt or "manual"

        # Try metadata cache first (no DB query needed)
        cached_meta = await get_cached_meme_metadata(template_id, texts)
        if cached_meta:
            return QuickMemeResponse(
                meme_id=cached_meta["meme_id"],
                image_url=cached_meta["image_url"],
                template_name=cached_meta["template_name"],
                meme_text=texts,
                cache_hit=True,
                generation_time_ms=int((time.monotonic() - t0) * 1000),
            )
    elif body.prompt:
        prompt = body.prompt.strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="prompt cannot be empty")

        cached_caps = await get_cached_captions(prompt)
        if cached_caps:
            best = cached_caps[0]
            template_id = int(best.get("meme_id", best.get("id")))
            texts = best.get("meme_text") or best.get("text") or best.get("captions", [])

            # Try metadata cache first (no DB query needed)
            cached_meta = await get_cached_meme_metadata(template_id, texts)
            if cached_meta:
                return QuickMemeResponse(
                    meme_id=cached_meta["meme_id"],
                    image_url=cached_meta["image_url"],
                    template_name=cached_meta["template_name"],
                    meme_text=texts,
                    cache_hit=True,
                    generation_time_ms=int((time.monotonic() - t0) * 1000),
                )
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either (template_id + captions) or prompt",
        )

    # ── 2. Cache Miss — Offload to ARQ worker & return 202 Accepted ───────────
    ai_provider = (body.ai_provider or "gemini").lower()
    generation_mode = "manual" if (body.template_id is not None and body.captions) else "auto"

    job_id = await enqueue_meme_generation(
        prompt=prompt,
        user=current_user,
        ai_provider=ai_provider,
        generation_mode=generation_mode,
        manual_template_id=body.template_id,
        manual_captions=body.captions,
    )

    return JSONResponse(
        status_code=202,
        content={"job_id": job_id, "status": "pending"}
    )


# ── Public meme listing ───────────────────────────────────────────────────────

@router.get("", response_model=MemeListResponse)
async def get_memes_alias(
    page: int = 1,
    limit: int = 20,
    sort: str = "recent",
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await get_public_memes(page, limit, sort, search, db)


@router.get("/public", response_model=MemeListResponse)
async def get_public_memes(
    page: int = 1,
    limit: int = 20,
    sort: str = "recent",
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    page = max(1, page)
    limit = min(100, limit)
    offset = (page - 1) * limit

    query = select(GeneratedMeme).where(GeneratedMeme.is_public == True)

    search_term = None
    if search:
        search_term = f"%{search}%"
        query = query.where(
            GeneratedMeme.prompt.ilike(search_term)
            | GeneratedMeme.template_name.ilike(search_term)
        )

    if sort == "top":
        query = query.order_by(desc(GeneratedMeme.share_count))
    elif sort == "trending":
        # ── Fast path: Redis sorted-set leaderboard ──────────────────
        trending_ids = await get_trending_meme_ids(offset, limit)
        if trending_ids:
            # Fetch only the memes whose IDs came back from Redis
            id_query = (
                select(GeneratedMeme)
                .where(
                    GeneratedMeme.is_public == True,
                    GeneratedMeme.id.in_(trending_ids),
                )
            )
            if search and search_term:
                id_query = id_query.where(
                    GeneratedMeme.prompt.ilike(search_term)
                    | GeneratedMeme.template_name.ilike(search_term)
                )
            result = await db.execute(id_query)
            memes_map = {m.id: m for m in result.scalars().all()}
            # Preserve the Redis ranking order
            memes = [memes_map[mid] for mid in trending_ids if mid in memes_map]

            count_q = select(func.count()).select_from(GeneratedMeme).where(
                GeneratedMeme.is_public == True
            )
            if search and search_term:
                count_q = count_q.where(
                    GeneratedMeme.prompt.ilike(search_term)
                    | GeneratedMeme.template_name.ilike(search_term)
                )
            total = (await db.execute(count_q)).scalar() or 0

            return MemeListResponse(
                memes=[
                    MemeResponse(
                        id=m.id,
                        template_name=m.template_name,
                        template_id=m.template_id,
                        prompt=m.prompt,
                        meme_text=m.meme_text,
                        image_url=m.image_url,
                        created_at=m.created_at.isoformat(),
                        share_count=m.share_count,
                        like_count=m.like_count,
                        is_public=m.is_public,
                    )
                    for m in memes
                ],
                total=total,
                page=page,
                limit=limit,
                has_more=offset + len(memes) < total,
            )

        # ── Fallback: indexed trending_score column ──────────────────
        query = query.order_by(desc(GeneratedMeme.trending_score))
    else:
        query = query.order_by(desc(GeneratedMeme.created_at))

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    memes = result.scalars().all()

    count_q = select(func.count()).select_from(GeneratedMeme).where(
        GeneratedMeme.is_public == True
    )
    if search and search_term:
        count_q = count_q.where(
            GeneratedMeme.prompt.ilike(search_term)
            | GeneratedMeme.template_name.ilike(search_term)
        )
    total = (await db.execute(count_q)).scalar() or 0

    return MemeListResponse(
        memes=[
            MemeResponse(
                id=m.id,
                template_name=m.template_name,
                template_id=m.template_id,
                prompt=m.prompt,
                meme_text=m.meme_text,
                image_url=m.image_url,
                created_at=m.created_at.isoformat(),
                share_count=m.share_count,
                like_count=m.like_count,
                is_public=m.is_public,
            )
            for m in memes
        ],
        total=total,
        page=page,
        limit=limit,
        has_more=offset + len(memes) < total,
    )


@router.get("/my", response_model=MemeListResponse)
async def get_my_memes(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    page = max(1, page)
    limit = min(100, limit)
    offset = (page - 1) * limit

    query = (
        select(GeneratedMeme)
        .where(GeneratedMeme.user_id == current_user.id)
        .order_by(desc(GeneratedMeme.created_at))
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    memes = result.scalars().all()

    count_q = select(func.count()).select_from(GeneratedMeme).where(
        GeneratedMeme.user_id == current_user.id
    )
    total = (await db.execute(count_q)).scalar() or 0

    return MemeListResponse(
        memes=[
            MemeResponse(
                id=m.id,
                template_name=m.template_name,
                template_id=m.template_id,
                prompt=m.prompt,
                meme_text=m.meme_text,
                image_url=m.image_url,
                created_at=m.created_at.isoformat(),
                share_count=m.share_count,
                like_count=m.like_count,
                is_public=m.is_public,
            )
            for m in memes
        ],
        total=total,
        page=page,
        limit=limit,
        has_more=offset + len(memes) < total,
    )


# ── Templates ─────────────────────────────────────────────────────────────────

@router.get("/templates", response_model=List[TemplateResponse])
async def get_templates(
    source: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        query = select(MemeTemplate)
        if source and source != "all":
            if source not in {"local", "database", "imgflip"}:
                raise HTTPException(status_code=400, detail="source must be local, database, imgflip, or all")
            query = query.where(MemeTemplate.source == source)
        query = query.order_by(MemeTemplate.id)

        result = await db.execute(query)
        templates = result.scalars().all()

        return [
            TemplateResponse(
                id=t.id,
                name=t.name,
                image_url=t.effective_image_url,
                text_field_count=t.number_of_text_fields,
                text_coordinates=t.text_coordinates or t.text_coordinates_xy_wh,
                preview_image_url=t.preview_image_url or t.effective_image_url,
                font_path=t.font_path,
                usage_instructions=t.usage_instructions,
                source=t.source,
                imgflip_id=t.imgflip_id,
            )
            for t in templates
        ]
    except Exception as exc:
        logger.error("Error fetching templates: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch templates")


@router.post("/templates/sync-imgflip")
async def sync_imgflip_templates(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    try:
        stats = await imgflip_service.sync_templates_to_db(db)
        return {"success": True, "message": "Successfully synced Imgflip templates", "stats": stats}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to sync: {str(exc)}")


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MemeTemplate).where(MemeTemplate.id == template_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")

    return TemplateResponse(
        id=t.id,
        name=t.name,
        image_url=t.effective_image_url,
        text_field_count=t.number_of_text_fields,
        text_coordinates=t.text_coordinates or t.text_coordinates_xy_wh,
        preview_image_url=t.preview_image_url or t.effective_image_url,
        font_path=t.font_path,
        usage_instructions=t.usage_instructions,
        source=t.source,
        imgflip_id=t.imgflip_id,
    )


# ── Individual meme actions ───────────────────────────────────────────────────

@router.get("/proxy-image")
async def proxy_template_image(url: str):
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(url, timeout=15.0, headers={"User-Agent": "MemeGPT/2.0"})
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "image/jpeg")
            if not content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="URL is not an image")
            return Response(
                content=resp.content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400, immutable",
                    "Access-Control-Allow-Origin": "*",
                    "X-Content-Type-Options": "nosniff",
                },
            )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail="Failed to fetch image")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Image fetch timeout")
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/{meme_id}", response_model=MemeResponse)
async def get_meme(meme_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GeneratedMeme).where(GeneratedMeme.id == meme_id))
    meme = result.scalar_one_or_none()
    if not meme or not meme.is_public:
        raise HTTPException(status_code=404, detail="Meme not found")

    return MemeResponse(
        id=meme.id,
        template_name=meme.template_name,
        template_id=meme.template_id,
        prompt=meme.prompt,
        meme_text=meme.meme_text,
        image_url=meme.image_url,
        created_at=meme.created_at.isoformat(),
        share_count=meme.share_count,
        like_count=meme.like_count,
        is_public=meme.is_public,
    )


@router.post("/{meme_id}/share")
async def share_meme(meme_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GeneratedMeme).where(GeneratedMeme.id == meme_id))
    meme = result.scalar_one_or_none()
    if not meme or not meme.is_public:
        raise HTTPException(status_code=404, detail="Meme not found")
    meme.share_count += 1
    meme.trending_score = compute_trending_score(meme.share_count, meme.like_count)
    await db.commit()
    # Update Redis leaderboard (fire-and-forget, failures are logged)
    await update_trending_score(meme.id, meme.share_count, meme.like_count)
    return {"message": "Share count updated", "share_count": meme.share_count}


@router.post("/{meme_id}/like")
async def like_meme(meme_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GeneratedMeme).where(GeneratedMeme.id == meme_id))
    meme = result.scalar_one_or_none()
    if not meme:
        raise HTTPException(status_code=404, detail="Meme not found")
    meme.like_count += 1
    meme.trending_score = compute_trending_score(meme.share_count, meme.like_count)
    await db.commit()
    await update_trending_score(meme.id, meme.share_count, meme.like_count)
    return {"message": "Liked", "liked": True, "like_count": meme.like_count}


@router.delete("/{meme_id}")
async def delete_meme(
    meme_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    result = await db.execute(select(GeneratedMeme).where(GeneratedMeme.id == meme_id))
    meme = result.scalar_one_or_none()
    if not meme:
        raise HTTPException(status_code=404, detail="Meme not found")
    if meme.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.delete(meme)
    await db.commit()
    await remove_from_trending(meme.id)
    return {"message": "Meme deleted successfully"}


# ── Template seeding ──────────────────────────────────────────────────────────

@router.post("/seed-templates")
async def seed_templates(db: AsyncSession = Depends(get_db)):
    meme_data_path = Path(__file__).parent.parent / "public" / "meme_data.json"
    if not meme_data_path.exists():
        raise HTTPException(status_code=500, detail="meme_data.json not found")

    with open(meme_data_path, encoding="utf-8") as f:
        templates_data = json.load(f)

    added = updated = 0

    for td in templates_data:
        tid = td["id"]
        result = await db.execute(select(MemeTemplate).where(MemeTemplate.id == tid))
        existing = result.scalar_one_or_none()

        fields = build_template_fields(td)

        if existing:
            for k, v in fields.items():
                setattr(existing, k, v)
            updated += 1
        else:
            db.add(MemeTemplate(id=tid, **fields))
            added += 1

    await db.commit()
    return {"message": "Templates seeded", "added": added, "updated": updated, "total": added + updated}
