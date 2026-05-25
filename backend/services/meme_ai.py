"""
AI caption generator — uses Google Gemini.

v2 enhancements:
  • Gen-Z cultural context injected into the system prompt
  • Structured JSON output with reasoning field
"""

from __future__ import annotations

import asyncio
import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from core.config import settings

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

ROOT_DIRECTORY = Path(__file__).resolve().parent.parent


class AIProvider(str, Enum):
    GEMINI = "gemini"


# ── Schemas ───────────────────────────────────────────────────────────────────

class MemeOutput(BaseModel):
    meme_id: int = Field(description="The integer ID of the template from the provided list")
    meme_name: str = Field(description="The name of the template")
    meme_text: List[str] = Field(description="The captions to place on the meme")
    reasoning: str = Field(description="One sentence explaining why this template fits the prompt")


class MemeList(BaseModel):
    output: List[MemeOutput] = Field(description="Exactly 3 generated meme options")


# ── Clients ───────────────────────────────────────────────────────────────────
gemini_client = genai.Client(
    api_key=settings.gemini_api_key
) if settings.gemini_api_key else None


# ── Template data ─────────────────────────────────────────────────────────────

# Load once at module import — eliminates repeated disk reads (called 6+ times per request)
_MEME_DATA_STR: str = ""
_MEME_DATA_LIST: list = []


def _load_meme_data_once() -> None:
    """Called once at module load time to populate in-memory caches."""
    global _MEME_DATA_STR, _MEME_DATA_LIST
    p = ROOT_DIRECTORY / "public" / "meme_data.json"
    with open(p, encoding="utf-8") as f:
        _MEME_DATA_STR = f.read()
    _MEME_DATA_LIST = json.loads(_MEME_DATA_STR)
    logger.info("Loaded %d meme templates into memory", len(_MEME_DATA_LIST))


_load_meme_data_once()


def load_meme_data() -> str:
    """Return the cached meme data JSON string (no disk I/O)."""
    return _MEME_DATA_STR


def get_meme_data_list() -> list:
    """Return the parsed meme template list (no disk I/O, no JSON parsing)."""
    return _MEME_DATA_LIST


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

CRITICAL: Follow the exact text field order specified in each template's usage_instructions.
The order matters for the meme to make sense!
"""

_OUTPUT_SCHEMA_DESC = "Return a JSON object with an 'output' array containing exactly 3 meme objects."


def _build_gemini_system(meme_data: str) -> str:
    return f"""You are a Gen-Z meme genius who creates hilarious, relatable memes.

{_GEN_Z_CONTEXT}

Available templates: {meme_data}

Rules:
- Choose 3 different templates that best fit the user's prompt
- **CRITICAL**: Follow the EXACT ORDER specified in usage_instructions for each template
- Text must be SHORT (max 10 words per field) and punchy
- Match the exact number of text fields per template
- Provide exactly 3 meme options with proper structure"""


# ── Gemini ────────────────────────────────────────────────────────────────────

async def generate_meme_captions_with_gemini(prompt: str) -> Optional[List[Dict[str, Any]]]:
    if not gemini_client:
        logger.warning("Gemini client not configured")
        return None

    meme_data = load_meme_data()
    try:
        # Configure safety settings to be more permissive for meme humor
        safety_settings = [
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_ONLY_HIGH"),
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_ONLY_HIGH"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_ONLY_HIGH"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_ONLY_HIGH"),
        ]

        config = types.GenerateContentConfig(
            system_instruction=_build_gemini_system(meme_data),
            max_output_tokens=2048,     # increased to prevent JSON truncation
            temperature=1.0,
            response_mime_type="application/json",
            response_schema=MemeList,
            safety_settings=safety_settings,
        )
        
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                # Use async generation
                resp = await gemini_client.aio.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=config
                )
                
                # 1. Candidate check
                if not resp.candidates:
                    logger.error("Gemini returned no candidates (attempt %d).", attempt + 1)
                    if attempt < max_retries:
                        continue
                    return None

                candidate = resp.candidates[0]
                
                # 2. Safety/Finish reason check
                if candidate.finish_reason not in ("STOP", "MAX_TOKENS", 1): # 1 was STOP in old SDK
                    logger.error("Gemini generation blocked/failed. Reason: %s (attempt %d)", candidate.finish_reason, attempt + 1)
                    if attempt < max_retries:
                        continue
                    return None

                # 3. Content extraction
                try:
                    raw = candidate.content.parts[0].text.strip()
                    logger.debug("Raw Gemini response (attempt %d): %s", attempt + 1, raw[:200])
                except (AttributeError, IndexError) as e:
                    logger.error("Failed to extract text from Gemini candidate: %s (attempt %d)", e, attempt + 1)
                    if attempt < max_retries:
                        continue
                    return None
                
                # 4. Parse Structured Output directly without brittle string manipulation hacks
                if not raw:
                    logger.error("Gemini returned empty response (attempt %d)", attempt + 1)
                    if attempt < max_retries:
                        continue
                    return None
                
                data = json.loads(raw)
                
                # Handle different response formats
                if isinstance(data, dict):
                    output = data.get("output", [])
                elif isinstance(data, list):
                    output = data
                else:
                    logger.error("Unexpected Gemini response format: %s", type(data))
                    if attempt < max_retries:
                        continue
                    return None
                
                # Validate the output structure
                if not output or not isinstance(output, list):
                    logger.error("Gemini returned empty or invalid output array")
                    if attempt < max_retries:
                        continue
                    return None
                
                # Validate each meme object has required fields
                valid_memes = []
                for meme in output:
                    if not isinstance(meme, dict):
                        logger.warning("Skipping invalid meme object: %s", meme)
                        continue
                    
                    # Check for required fields with flexible naming
                    meme_id = meme.get("meme_id") or meme.get("id") or meme.get("template_id")
                    meme_name = meme.get("meme_name") or meme.get("name") or meme.get("template_name")
                    meme_text = meme.get("meme_text") or meme.get("text") or meme.get("captions") or meme.get("input_texts")
                    
                    # If we have template_name but no ID, try to look it up
                    if meme_id is None and meme_name:
                        try:
                            meme_data_obj = get_meme_data_list()  # in-memory, no disk/json overhead
                            # Try exact match first
                            template = next((t for t in meme_data_obj if t["name"].lower() == meme_name.lower()), None)
                            if template:
                                meme_id = template["id"]
                                logger.debug("Looked up template ID %d for name '%s'", meme_id, meme_name)
                        except Exception as e:
                            logger.warning("Failed to look up template ID for name '%s': %s", meme_name, e)
                    
                    if meme_id is None or not meme_name or not meme_text:
                        logger.warning("Skipping incomplete meme object (missing ID, name, or text): %s", meme)
                        continue
                    
                    # Normalize the meme object
                    normalized_meme = {
                        "meme_id": int(meme_id),
                        "meme_name": str(meme_name),
                        "meme_text": list(meme_text) if isinstance(meme_text, list) else [str(meme_text)],
                        "reasoning": meme.get("reasoning", "Generated by Gemini")
                    }
                    valid_memes.append(normalized_meme)
                
                if not valid_memes:
                    logger.error("No valid memes found in Gemini response (attempt %d)", attempt + 1)
                    if attempt < max_retries:
                        continue
                    return None
                
                logger.info("Gemini generated %d valid memes on attempt %d", len(valid_memes), attempt + 1)
                return valid_memes
                
            except json.JSONDecodeError as e:
                logger.error("JSONDecodeError on Gemini attempt %d: %s. Raw output: %s", attempt + 1, e, raw[:500] if 'raw' in locals() else '')
                if attempt < max_retries:
                    logger.info("Retrying Gemini generation (attempt %d of %d)...", attempt + 2, max_retries + 1)
                    continue
                logger.error("Gemini failed after %d attempts due to JSONDecodeError", max_retries + 1)
                return None
            except Exception as exc:
                logger.exception("Gemini caption generation failed on attempt %d: %s", attempt + 1, exc)
                if attempt < max_retries:
                    continue
                return None

        return None
            
    except Exception as exc:
        logger.exception("Gemini configuration/execution failed: %s", exc)
        return None


async def _generate_captions(prompt: str) -> Optional[List[Dict[str, Any]]]:
    """Generate captions using Gemini."""
    return await generate_meme_captions_with_gemini(prompt)

# ── Factory ───────────────────────────────────────────────────────────────────

async def get_caption_generator(provider: Optional[str] = None):
    """Return a caption generator using Gemini."""
    
    async def robust_generator(prompt: str) -> Optional[List[Dict[str, Any]]]:
        try:
            # 20-second timeout guard on overall generation
            return await asyncio.wait_for(generate_meme_captions_with_gemini(prompt), timeout=20.0)
        except asyncio.TimeoutError:
            logger.error("AI caption generation timed out after 20 seconds")
            return None
        except Exception as exc:
            logger.error("Caption generation failed: %s", exc)
            return None

    return robust_generator
