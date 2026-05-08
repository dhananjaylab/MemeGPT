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

from google import genai
from google.genai import types
from openai import AsyncOpenAI

from core.config import settings

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

ROOT_DIRECTORY = Path(__file__).resolve().parent.parent.parent


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

_OUTPUT_SCHEMA_DESC = "Return a JSON object with an 'output' array containing exactly 3 meme objects."


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

Provide exactly 3 meme options with proper JSON structure."""


def _build_gemini_system(meme_data: str) -> str:
    return f"""You are a Gen-Z meme genius who creates hilarious, relatable memes.

{_GEN_Z_CONTEXT}

Available templates: {meme_data}

Rules:
- Choose 3 different templates that best fit the user's prompt
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
            output = data.get("memes", data.get("results", data.get("meme_options", data.get("options", []))))
        
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
            meme_text = meme.get("meme_text") or meme.get("text") or meme.get("captions") or meme.get("text_fields") or meme.get("input_texts")
            
            if meme_id is None or not meme_text:
                logger.warning("Skipping incomplete meme object: %s", meme)
                continue
            
            # For OpenAI, we might need to look up the template name if not provided
            if not meme_name:
                # Try to get template name from the meme data if we have template_id
                try:
                    meme_data_obj = json.loads(load_meme_data())
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
            max_output_tokens=2048,
            temperature=1.0,
            response_mime_type="application/json",
            response_schema=MemeList,
            safety_settings=safety_settings,
        )
        
        # Use async generation
        resp = await gemini_client.aio.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
            config=config
        )
        
        # 1. Candidate check
        if not resp.candidates:
            logger.error("Gemini returned no candidates.")
            return None

        candidate = resp.candidates[0]
        
        # 2. Safety/Finish reason check
        # In new SDK, finish_reason is an enum/string
        if candidate.finish_reason not in ("STOP", "MAX_TOKENS", 1): # 1 was STOP in old SDK
            logger.error("Gemini generation blocked/failed. Reason: %s", candidate.finish_reason)
            return None

        # 3. Content extraction
        try:
            raw = candidate.content.parts[0].text.strip()
            logger.debug("Raw Gemini response: %s", raw[:200])
        except (AttributeError, IndexError) as e:
            logger.error("Failed to extract text from Gemini candidate: %s", e)
            return None
        
        # 4. Parse Structured Output
        try:
            # With response_schema, the output should be clean JSON
            # But sometimes there might be truncated responses, so let's be more robust
            if not raw:
                logger.error("Gemini returned empty response")
                return None
                
            # Try to fix common JSON issues
            if raw.count('"') % 2 != 0:
                logger.warning("Detected unterminated string in Gemini response, attempting to fix")
                # Find the last complete object
                last_complete = raw.rfind('"}')
                if last_complete > 0:
                    # Try to close the JSON properly
                    raw = raw[:last_complete + 2] + ']}'
                    logger.debug("Attempted JSON fix: %s", raw[-50:])
            
            data = json.loads(raw)
            
            # Handle different response formats
            if isinstance(data, dict):
                output = data.get("output", [])
            elif isinstance(data, list):
                output = data
            else:
                logger.error("Unexpected Gemini response format: %s", type(data))
                return None
            
            # Validate the output structure
            if not output or not isinstance(output, list):
                logger.error("Gemini returned empty or invalid output array")
                return None
            
            # Validate each meme object has required fields
            valid_memes = []
            for meme in output:
                if not isinstance(meme, dict):
                    logger.warning("Skipping invalid meme object: %s", meme)
                    continue
                
                # Check for required fields with flexible naming
                meme_id = meme.get("meme_id") or meme.get("id")
                meme_name = meme.get("meme_name") or meme.get("name")
                meme_text = meme.get("meme_text") or meme.get("text") or meme.get("captions")
                
                if meme_id is None or not meme_name or not meme_text:
                    logger.warning("Skipping incomplete meme object: %s", meme)
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
                logger.error("No valid memes found in Gemini response")
                return None
            
            logger.info("Gemini generated %d valid memes", len(valid_memes))
            return valid_memes
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse Gemini JSON. Error: %s, Raw output: %s", e, raw[:500])
            return None
            
    except Exception as exc:
        logger.exception("Gemini caption generation failed: %s", exc)
        return None


# ── Factory ───────────────────────────────────────────────────────────────────

async def get_caption_generator(provider: Optional[str] = None):
    """Return a robust caption generator with built-in provider failover."""
    requested_provider = (provider or settings.ai_provider).lower()

    async def robust_generator(prompt: str) -> Optional[List[Dict[str, Any]]]:
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
