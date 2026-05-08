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
        # Configure safety settings to be more permissive for meme humor
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
        ]

        model = genai.GenerativeModel(
            model_name="gemini-3-flash-preview",
            system_instruction=_build_gemini_system(meme_data),
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=2048,
                temperature=1.0,
                response_mime_type="application/json",
            ),
            safety_settings=safety_settings
        )
        
        # Use async generation
        resp = await model.generate_content_async(prompt)
        
        # 1. Candidate check
        if not resp.candidates:
            logger.error("Gemini returned no candidates. Prompt feedback: %s", getattr(resp, 'prompt_feedback', 'N/A'))
            return None

        candidate = resp.candidates[0]
        
        # 2. Safety/Finish reason check
        # finish_reason 1 is STOP (Success), others usually mean blocked or error
        if candidate.finish_reason != 1:
            logger.error("Gemini generation blocked/failed. Reason: %s. Safety: %s", 
                         candidate.finish_reason, 
                         [{"category": r.category, "rating": r.probability} for r in candidate.safety_ratings] if hasattr(candidate, 'safety_ratings') else "N/A")
            return None

        # 3. Content extraction
        try:
            raw = candidate.content.parts[0].text.strip()
        except (AttributeError, IndexError) as e:
            logger.error("Failed to extract text from Gemini candidate: %s", e)
            return None
        
        # 4. Robust JSON Parsing
        json_str = raw
        if "```json" in raw:
            json_str = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            json_str = raw.split("```")[1].split("```")[0].strip()
        
        try:
            data = json.loads(json_str)
            # Support both {"output": [...]} and a direct array if the model gets confused
            if isinstance(data, dict):
                return data.get("output", [])
            elif isinstance(data, list):
                return data
            return None
        except json.JSONDecodeError:
            logger.error("Failed to parse Gemini JSON. Raw output: %s", raw[:500])
            # Last resort: try regex
            import re
            match = re.search(r'(\{.*\}|\[.*\])', raw, re.DOTALL)
            if match:
                try:
                    extracted = json.loads(match.group(1))
                    if isinstance(extracted, dict): return extracted.get("output", [])
                    if isinstance(extracted, list): return extracted
                except:
                    pass
            return None
    except Exception as exc:
        logger.exception("Gemini caption generation failed: %s", exc)
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
