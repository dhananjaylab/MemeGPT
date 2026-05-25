"""
Meme compositor — draws text on template images.

Improvements over v1:
  • Supports remote template images (URL download with Redis caching)
  • Async-first interface (`overlay_text_on_image_async`)
  • Sync wrapper kept for backward-compat with the ARQ worker
  • Better kerning: uses `getbbox` instead of deprecated `getsize`
  • Gen-Z font auto-scaling tuned for short, punchy captions
  • Remote-first: prefers CDN URLs over local files when available
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import io
import logging
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from uuid import uuid4

import httpx
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT_DIRECTORY  = Path(__file__).resolve().parent.parent
IMAGE_FOLDER    = ROOT_DIRECTORY / "public" / "frames"
FONT_FOLDER     = ROOT_DIRECTORY / "public" / "fonts"
OUTPUT_FOLDER   = ROOT_DIRECTORY / "public" / "output"
LINE_HEIGHT_MUL = 1.35   # slightly tighter than v1 — feels more meme-y


# ── Tiny helpers ─────────────────────────────────────────────────────────────

def _to_upper(font_name: str, text: str) -> str:
    return text.upper() if font_name.lower() == "impact.ttf" else text


def _char_width(font: ImageFont.FreeTypeFont, font_name: str) -> int:
    sample = _to_upper(font_name, "A")
    bb = font.getbbox(sample)
    return max(1, bb[2] - bb[0])


def _text_height(draw: ImageDraw.ImageDraw, lines: List[str],
                 font: ImageFont.FreeTypeFont) -> int:
    total = 0
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font)
        total += bb[3] - bb[1]
    return int(total * LINE_HEIGHT_MUL)


def _unique_output_path() -> Path:
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    return OUTPUT_FOLDER / f"{uuid4()}.png"


# ── Remote image fetching (with Redis cache) ──────────────────────────────────

async def _fetch_remote_image(url: str) -> Image.Image:
    """Download a template image, caching the raw bytes in Redis."""
    # Inline import to avoid circular deps
    from services.cache import get_cached_template_image, set_cached_template_image

    cached = await get_cached_template_image(url)
    if cached:
        return Image.open(io.BytesIO(cached))

    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        resp = await client.get(url, headers={"User-Agent": "MemeGPT-Compositor/2.0"})
        resp.raise_for_status()
        image_bytes = resp.content

    await set_cached_template_image(url, image_bytes)
    return Image.open(io.BytesIO(image_bytes))


async def _load_template_image(
    file_path: str,
    image_url: Optional[str] = None,
) -> Image.Image:
    """
    Load a template image — remote-first strategy.

    Priority:
      1. Remote URL if available (downloaded + cached via Redis)
      2. Local file in backend/public/frames/ as fallback
    This minimises dependency on local filesystem state.
    """
    # ── Try remote URL first (preferred for CDN-hosted templates) ────────────
    if image_url:
        resolved_url = image_url
        # Strip our own proxy wrapper so we hit the origin CDN
        if resolved_url.startswith("/api/memes/proxy-image?url="):
            resolved_url = resolved_url[len("/api/memes/proxy-image?url="):]
        elif resolved_url.startswith("/frames/"):
            # This is a local-relative URL — fall through to local check
            resolved_url = None

        if resolved_url and resolved_url.startswith("http"):
            try:
                logger.info("Fetching remote template: %s", resolved_url[:100])
                return await _fetch_remote_image(resolved_url)
            except Exception as exc:
                logger.warning("Remote fetch failed (%s), trying local: %s", resolved_url[:60], exc)

    # ── Fallback: local file ─────────────────────────────────────────────────
    if file_path:
        local = IMAGE_FOLDER / file_path
        if local.exists() and local.is_file():
            return Image.open(local)

    logger.error("Template image not found: remote=%r, local=%s. Using blank fallback.", image_url, file_path)
    # Generate a blank fallback image to prevent pipeline crash
    return Image.new("RGB", (800, 800), color=(40, 40, 40))


# ── Core text-drawing logic ───────────────────────────────────────────────────

def _draw_text_box(
    draw: ImageDraw.ImageDraw,
    text: str,
    bbox: Tuple[int, int, int, int],  # (x, y, box_width, box_height)
    font_name: str,
    text_color: str,
    text_stroke: bool,
    font_size_hint: int = 8,
) -> None:
    """
    Fit `text` into a bounding box, auto-scaling the font to fill it.
    Renders with optional black/white stroke for legibility.
    """
    x, y, box_width, box_height = bbox
    text = _to_upper(font_name, text)
    font_file = str(FONT_FOLDER / font_name)

    try:
        font = ImageFont.truetype(font_file, font_size_hint)
    except (OSError, IOError):
        font = ImageFont.load_default()

    # Grow font until text overflows the box
    font_size = font_size_hint
    while True:
        cw = _char_width(font, font_name)
        wrap_w = max(1, box_width // max(1, cw))
        lines = textwrap.wrap(text, break_long_words=False, width=wrap_w) or [text]
        total_h = _text_height(draw, lines, font)
        max_line_w = max(
            (draw.textbbox((0, 0), l, font=font)[2] for l in lines), default=0
        )

        if total_h >= box_height or max_line_w >= box_width:
            break

        font_size += 1
        try:
            font = ImageFont.truetype(font_file, font_size)
        except (OSError, IOError):
            break

    # Step back one to stay inside box
    font_size = max(8, font_size - 1)
    try:
        font = ImageFont.truetype(font_file, font_size)
    except (OSError, IOError):
        font = ImageFont.load_default()

    cw = _char_width(font, font_name)
    wrap_w = max(1, box_width // max(1, cw))
    lines = textwrap.wrap(text, break_long_words=False, width=wrap_w) or [text]
    total_h = _text_height(draw, lines, font)

    text_y = y + max(0, (box_height - total_h) / 2)

    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font)
        line_w = bb[2] - bb[0]
        line_h = bb[3] - bb[1]
        text_x = x + (box_width - line_w) / 2

        if text_stroke:
            sw = max(1, _char_width(font, font_name) // 6)
            stroke_fill = "black" if text_color.lower() in ("#ffffff", "white") else "white"
            draw.text(
                (text_x, text_y), line, font=font,
                fill=text_color, stroke_width=sw, stroke_fill=stroke_fill,
            )
        else:
            draw.text((text_x, text_y), line, font=font, fill=text_color)

        text_y += line_h * LINE_HEIGHT_MUL


# ── Public async interface ────────────────────────────────────────────────────

executor = ThreadPoolExecutor(max_workers=8)


def _sync_overlay_text(
    img: Image.Image,
    meme: Dict[str, Any],
    texts: List[str],
) -> Path:
    """Pure synchronous function executing CPU-bound Pillow operations."""
    draw = ImageDraw.Draw(img)

    for bbox, text in zip(meme["text_coordinates_xy_wh"], texts):
        _draw_text_box(
            draw=draw,
            text=text,
            bbox=tuple(bbox),
            font_name=meme["font_path"],
            text_color=meme.get("text_color", "white"),
            text_stroke=meme.get("text_stroke", True),
        )

    out = _unique_output_path()
    # Save as JPEG: ~3-5x faster to encode than PNG and ~60% smaller
    # (the storage layer re-encodes to WebP anyway)
    out = out.with_suffix(".jpg")
    # Ensure RGB (JPEG doesn't support alpha)
    if img.mode in ("RGBA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")
    img.save(out, format="JPEG", quality=88, optimize=True)
    return out


async def overlay_text_on_image_async(
    meme: Dict[str, Any],
    texts: List[str],
) -> Path:
    """
    Async version — downloads remote template images when needed.
    Returns path to the newly created output PNG.
    """
    img = await _load_template_image(
        meme["file_path"],
        meme.get("image_url"),
    )

    loop = asyncio.get_running_loop()
    # Execute the blocking CPU-bound PIL code in a thread
    return await loop.run_in_executor(
        executor,
        _sync_overlay_text,
        img,
        meme,
        texts,
    )


# ── Sync shim (for backward compat) ──────────────────────────────────────────

def overlay_text_on_image(
    meme: Dict[str, Any],
    texts: List[str],
) -> Path:
    """
    Sync wrapper around the async compositor.
    Used by the ARQ worker (which runs in its own event loop).
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're already inside an async context — run in thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    overlay_text_on_image_async(meme, texts),
                )
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(overlay_text_on_image_async(meme, texts))
    except Exception:
        # Hard fallback: try local PIL only (no URL support)
        return _overlay_local_only(meme, texts)


def _overlay_local_only(meme: Dict[str, Any], texts: List[str]) -> Path:
    """Fallback compositor that only reads local files."""
    file_path = meme.get("file_path")
    if file_path:
        image_path = IMAGE_FOLDER / file_path
        if image_path.exists() and image_path.is_file():
            img = Image.open(image_path)
        else:
            img = Image.new("RGB", (800, 800), color=(40, 40, 40))
    else:
        img = Image.new("RGB", (800, 800), color=(40, 40, 40))
    draw = ImageDraw.Draw(img)

    for bbox, text in zip(meme["text_coordinates_xy_wh"], texts):
        _draw_text_box(
            draw=draw,
            text=text,
            bbox=tuple(bbox),
            font_name=meme["font_path"],
            text_color=meme.get("text_color", "white"),
            text_stroke=meme.get("text_stroke", True),
        )

    out = _unique_output_path()
    img.save(out, format="PNG", optimize=True)
    return out
