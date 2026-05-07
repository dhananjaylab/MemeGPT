"""
AI caption generator — supports OpenAI GPT-4o and Google Gemini.

v2 enhancements:
  • Gen-Z cultural context injected into the system prompt
  • Structured JSON output with reasoning field
  • Fallback chain: primary provider → fallback provider → error
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from openai import AsyncOpenAI

from core.config import settings

logger = logging.getLogger(__name__)

ROOT_DIRECTORY = Path(__file__).resolve().parent.parent.parent


class AIProvider(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    BOTH   = "both"


# ── Clients ───────────────────────────────────────────────────────────────────
openai_client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)


# ── Template data ─────────────────────────────────────────────────────────────

def load_meme_data() -> str:
    p = ROOT_DIRECTORY / "public" / "meme_data.json"
    with open(p, encoding="utf-8") as f:
        return f.read()


# ── System prompts ────────────────────────────────────────────────────────────

_GEN_Z_CONTEXT = """
CULTURAL CONTEXT — GEN-Z INTERNET HUMOR (2023-2025):
• Tone: dry, self-aware, absurdist, slightly nihilistic but fun
• Common formats: "no cap", "lowkey/highkey", "it's giving X", "understood the assignment",
  "rent free", "main character", "this is fine", "NPC behavior", "slay/based/sigma",
  "touch grass", "the audacity", "rizz", "understood the assignment", "vibe check"
• Humor often comes from relatable mundane struggles, internet addiction, hustle culture
  irony, academic pressure, social anxiety, and absurd escalation
• Short punchy captions beat long ones — aim for impact in ≤ 8 words per field
• Self-deprecating and situational > preachy or lecture-y
"""

_OUTPUT_SCHEMA = """
Return ONLY a valid JSON object (no markdown, no code fences) with this shape:
{
  "output": [
    {
      "meme_id": <integer>,
      "meme_name": "<string>",
      "meme_text": ["<text1>", "<text2>", ...],
      "reasoning": "<one sentence>"
    }
    // exactly 3 items
  ]
}
"""


def _build_openai_system(meme_data: str) -> str:
    return f"""You are a Gen-Z meme genius who creates hilarious, relatable memes.

{_GEN_Z_CONTEXT}

AVAILABLE TEMPLATES:
{meme_data}

RULES:
1. Pick 3 DIFFERENT templates — variety is key.
2. Match the template structure exactly (number of text fields, tone).
3. Keep text SHORT and punchy (max 10 words per field).
4. Be funny, not cringe. Lean into current internet culture.
5. The first option should be the most relatable/mainstream.
6. The second option can be more niche/absurdist.
7. The third option should be the wildcard / unexpected angle.

{_OUTPUT_SCHEMA}"""


def _build_gemini_system(meme_data: str) -> str:
    return f"""You are a Gen-Z meme genius who creates hilarious, relatable memes.

{_GEN_Z_CONTEXT}

Available templates: {meme_data}

Rules:
- Choose 3 different templates that best fit the user's prompt
- Text must be SHORT (max 10 words per field) and punchy
- Match the exact number of text fields per template
- Return ONLY valid JSON, no extra text

{_OUTPUT_SCHEMA}"""


# ── OpenAI ────────────────────────────────────────────────────────────────────

async def generate_meme_captions(prompt: str) -> Optional[List[Dict[str, Any]]]:
    if not openai_client:
        logger.warning("OpenAI client not configured")
        return None

    meme_data = load_meme_data()
    try:
        resp = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _build_openai_system(meme_data)},
                {"role": "user",   "content": prompt},
            ],
            temperature=1.1,    # slightly higher for more creative Gen-Z output
            max_tokens=2048,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or ""
        data = json.loads(content)
        return data.get("output", [])
    except Exception as exc:
        logger.error("OpenAI caption generation failed: %s", exc)
        return None


# ── Gemini ────────────────────────────────────────────────────────────────────

async def generate_meme_captions_with_gemini(prompt: str) -> Optional[List[Dict[str, Any]]]:
    if not settings.gemini_api_key:
        logger.warning("Gemini API key not configured")
        return None

    meme_data = load_meme_data()
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=_build_gemini_system(meme_data),
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=2048,
                temperature=1.0,
                response_mime_type="application/json",
            ),
        )
        resp = model.generate_content(prompt)
        raw = (resp.text or "").strip()
        # Strip accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        return data.get("output", [])
    except Exception as exc:
        logger.error("Gemini caption generation failed: %s", exc)
        return None


# ── Factory ───────────────────────────────────────────────────────────────────

async def get_caption_generator(provider: Optional[str] = None):
    """Return the best available caption generator for the requested provider."""
    p = (provider or settings.ai_provider).lower()

    if p == AIProvider.GEMINI.value and settings.has_gemini:
        return generate_meme_captions_with_gemini

    if p == AIProvider.OPENAI.value and settings.has_openai:
        return generate_meme_captions

    # Fallback: use whichever is configured
    if settings.has_openai:
        return generate_meme_captions
    if settings.has_gemini:
        return generate_meme_captions_with_gemini

    raise RuntimeError("No AI provider configured — set OPENAI_API_KEY or GEMINI_API_KEY")
