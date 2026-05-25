"""
AI caption generator — supports OpenAI GPT-4o and Google Gemini.

v2 enhancements:
  • Gen-Z cultural context injected into the system prompt
  • Structured JSON output with reasoning field
  • Fallback chain: primary provider → fallback provider → error
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
from openai import AsyncOpenAI

from core.config import settings

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

ROOT_DIRECTORY = Path(__file__).resolve().parent.parent


class AIProvider(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    BOTH   = "both"


# ── Schemas ───────────────────────────────────────────────────────────────────

class MemeOutput(BaseModel):
    meme_id: int = Field(description="The integer ID of the template from the provided list")
    meme_name: str = Field(description="The name of the template")
    meme_text: List[str] = Field(description="The captions to place on the meme")
    reasoning: str = Field(description="One sentence explaining why this template fits the prompt")


class MemeList(BaseModel):
    output: List[MemeOutput] = Field(description="Exactly 3 generated meme options")


# ── Clients ───────────────────────────────────────────────────────────────────
openai_client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

gemini_client = genai.Client(api_key=settings.gemini_api_key) if settings.gemini_api_key else None


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


def _build_openai_system(meme_data: str) -> str:
    return f"""You are a Gen-Z meme genius who creates hilarious, relatable memes.

{_GEN_Z_CONTEXT}

AVAILABLE TEMPLATES:
{meme_data}

RULES:
1. Pick 3 DIFFERENT templates — variety is key.
2. Match the template structure exactly (number of text fields, tone).
3. **CRITICAL**: Follow the EXACT ORDER specified in usage_instructions for each template.
   - For "Distracted Boyfriend": [seductive thing, person, current commitment]
   - For "Left Exit 12": [main road, person, exit road]
   - Read the usage_instructions carefully and follow the field order!
4. Keep text SHORT and punchy (max 10 words per field).
5. Be funny, not cringe. Lean into current internet culture.
6. The first option should be the most relatable/mainstream.
7. The second option can be more niche/absurdist.
8. The third option should be the wildcard / unexpected angle.

Provide exactly 3 meme options with proper JSON structure."""


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


# ── OpenAI ────────────────────────────────────────────────────────────────────

async def generate_meme_captions(prompt: str) -> Optional[List[Dict[str, Any]]]:
    if not openai_client:
        logger.warning("OpenAI client not configured")
        return None

    meme_data = load_meme_data()
    try:
        resp = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _build_openai_system(meme_data)},
                {"role": "user",   "content": prompt},
            ],
            temperature=1.1,    # slightly higher for more creative Gen-Z output
            max_tokens=512,     # actual output is ~200-300 tokens; 2048 wastes reservation time
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "meme_list",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "output": {
                                "type": "array",
                                "description": "Exactly 3 generated meme options",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "meme_id": {
                                            "type": "integer",
                                            "description": "The integer ID of the template from the provided list"
                                        },
                                        "meme_name": {
                                            "type": "string",
                                            "description": "The name of the template"
                                        },
                                        "meme_text": {
                                            "type": "array",
                                            "description": "The captions to place on the meme",
                                            "items": {
                                                "type": "string"
                                            }
                                        },
                                        "reasoning": {
                                            "type": "string",
                                            "description": "One sentence explaining why this template fits the prompt"
                                        }
                                    },
                                    "required": ["meme_id", "meme_name", "meme_text", "reasoning"],
                                    "additionalProperties": False
                                }
                            }
                        },
                        "required": ["output"],
                        "additionalProperties": False
                    }
                }
            },
        )
        
        content = resp.choices[0].message.content or ""
        if not content.strip():
            logger.error("OpenAI returned empty content")
            return None
            
        logger.debug("Raw OpenAI response: %s", content[:200])
        
        data = json.loads(content)
        
        # Debug logging
        logger.debug("OpenAI response structure: %s", list(data.keys()) if isinstance(data, dict) else type(data))
        
        output = data.get("output", [])
        
        # If output is empty, check if the data itself is the array
        if not output and isinstance(data, list):
            output = data
        elif not output and isinstance(data, dict):
            # Check for alternative keys (OpenAI uses different response formats)
            output = data.get("memes", data.get("results", data.get("meme_options", data.get("options", data.get("examples", [])))))
        
        if not output or not isinstance(output, list):
            logger.error("OpenAI returned empty or invalid output array. Data keys: %s", list(data.keys()) if isinstance(data, dict) else "Not a dict")
            return None
        
        # Validate each meme object has required fields
        valid_memes = []
        for meme in output:
            if not isinstance(meme, dict):
                logger.warning("Skipping invalid meme object: %s", meme)
                continue
            
            # Check for required fields with flexible naming (OpenAI uses different field names)
            meme_id = meme.get("meme_id") or meme.get("id") or meme.get("template_id")
            meme_name = meme.get("meme_name") or meme.get("name") or meme.get("template_name")
            meme_text = (meme.get("meme_text") or meme.get("text") or meme.get("captions") or 
                        meme.get("text_fields") or meme.get("input_texts") or 
                        meme.get("fields") or meme.get("output"))
            
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
            
            if meme_id is None or not meme_text:
                logger.warning("Skipping incomplete meme object (missing ID or text): %s", meme)
                continue
            
            # For OpenAI, we might need to look up the template name if not provided
            if not meme_name:
                # Try to get template name from the meme data if we have template_id
                try:
                    meme_data_obj = get_meme_data_list()  # in-memory, no disk/json overhead
                    template = next((t for t in meme_data_obj if t["id"] == int(meme_id)), None)
                    meme_name = template["name"] if template else f"Template {meme_id}"
                except:
                    meme_name = f"Template {meme_id}"
            
            # Normalize the meme object
            normalized_meme = {
                "meme_id": int(meme_id),
                "meme_name": str(meme_name),
                "meme_text": list(meme_text) if isinstance(meme_text, list) else [str(meme_text)],
                "reasoning": meme.get("reasoning", "Generated by OpenAI")
            }
            valid_memes.append(normalized_meme)
        
        if not valid_memes:
            logger.error("No valid memes found in OpenAI response")
            return None
        
        logger.info("OpenAI generated %d valid memes", len(valid_memes))
        return valid_memes
        
    except json.JSONDecodeError as e:
        logger.error("Failed to parse OpenAI JSON. Error: %s, Content: %s", e, content[:500])
        return None
    except Exception as exc:
        logger.error("OpenAI caption generation failed: %s", exc)
        return None


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
            max_output_tokens=512,     # actual output is ~200-300 tokens; reducing saves latency
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
                    model="gemini-3-flash-preview",
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


async def _race_generators(prompt: str) -> Optional[List[Dict[str, Any]]]:
    """Race OpenAI and Gemini concurrently, returning the first successful result."""
    tasks = []
    if settings.has_openai:
        tasks.append(asyncio.create_task(generate_meme_captions(prompt)))
    if settings.has_gemini:
        tasks.append(asyncio.create_task(generate_meme_captions_with_gemini(prompt)))

    if not tasks:
        logger.error("Cannot race AI providers: No providers configured")
        return None

    while tasks:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            try:
                result = task.result()
                if result and len(result) > 0:
                    # Cancel any pending slow tasks
                    for p in pending:
                        p.cancel()
                    return result
            except Exception as e:
                logger.error("Racing task failed: %s", e)
        tasks = list(pending)

    return None

# ── Factory ───────────────────────────────────────────────────────────────────

async def get_caption_generator(provider: Optional[str] = None):
    """Return a robust caption generator with built-in provider failover and racing."""
    requested_provider = (provider or settings.ai_provider).lower()

    async def robust_generator(prompt: str) -> Optional[List[Dict[str, Any]]]:
        try:
            # 20-second timeout guard on overall generation
            return await asyncio.wait_for(_run_generation(prompt), timeout=20.0)
        except asyncio.TimeoutError:
            logger.error("AI caption generation timed out after 20 seconds")
            return None

    async def _run_generation(prompt: str) -> Optional[List[Dict[str, Any]]]:
        # If explicit race requested, or if not strictly requesting one and both are available
        if requested_provider == AIProvider.BOTH.value or (requested_provider not in [AIProvider.OPENAI.value, AIProvider.GEMINI.value] and settings.has_openai and settings.has_gemini):
            logger.info("Racing AI providers concurrently...")
            return await _race_generators(prompt)

        # 1. Try requested provider first
        if requested_provider == AIProvider.GEMINI.value and settings.has_gemini:
            logger.info("Attempting caption generation with Gemini...")
            result = await generate_meme_captions_with_gemini(prompt)
            if result and len(result) > 0:
                logger.info("Gemini generation successful")
                return result
            logger.warning("Gemini failed or returned empty results, falling back to OpenAI...")

        elif requested_provider == AIProvider.OPENAI.value and settings.has_openai:
            logger.info("Attempting caption generation with OpenAI...")
            result = await generate_meme_captions(prompt)
            if result and len(result) > 0:
                logger.info("OpenAI generation successful")
                return result
            logger.warning("OpenAI failed or returned empty results, falling back to Gemini...")

        # 2. Try fallback provider if primary failed
        if requested_provider == AIProvider.GEMINI.value and settings.has_openai:
            logger.info("Attempting fallback to OpenAI...")
            result = await generate_meme_captions(prompt)
            if result and len(result) > 0:
                logger.info("OpenAI fallback successful")
                return result
            logger.error("Both Gemini and OpenAI failed")
        
        elif requested_provider == AIProvider.OPENAI.value and settings.has_gemini:
            logger.info("Attempting fallback to Gemini...")
            result = await generate_meme_captions_with_gemini(prompt)
            if result and len(result) > 0:
                logger.info("Gemini fallback successful")
                return result
            logger.error("Both OpenAI and Gemini failed")

        # 3. If no provider was configured for the requested type, try any available
        if not settings.has_gemini and not settings.has_openai:
            logger.error("No AI providers configured")
            return None

        if requested_provider == AIProvider.GEMINI.value and not settings.has_gemini:
            if settings.has_openai:
                logger.warning("Gemini not configured, using OpenAI instead")
                return await generate_meme_captions(prompt)
        
        if requested_provider == AIProvider.OPENAI.value and not settings.has_openai:
            if settings.has_gemini:
                logger.warning("OpenAI not configured, using Gemini instead")
                return await generate_meme_captions_with_gemini(prompt)

        logger.error("All caption generation attempts failed")
        return None

    return robust_generator
