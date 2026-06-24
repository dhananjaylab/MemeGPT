"""
AI caption generator — Gemini primary, Anthropic automatic fallback.

v2 enhancements:
  • Gen-Z cultural context injected into the system prompt
  • Structured JSON output with reasoning field

Phase 2 enhancements:
  • Anthropic fallback (services/meme_ai.py previously had ANTHROPIC_API_KEY
    configured in every env file but no code path ever used it — a Gemini
    outage took down 100% of generation).
  • Gemini safety thresholds tightened from BLOCK_ONLY_HIGH to
    BLOCK_MEDIUM_AND_ABOVE on every category — BLOCK_ONLY_HIGH was the most
    permissive tier available and let a meaningful amount of medium-severity
    content straight through with nothing downstream reviewing it.
  • A small circuit breaker (services/circuit_breaker.py) stops every
    request from individually waiting out a 20s timeout against a Gemini
    outage before falling back — after a few consecutive failures it skips
    straight to Anthropic until a recovery window has passed.
"""

from __future__ import annotations

import asyncio
import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

# google-genai 1.46.x still references aiohttp.ClientConnectorDNSError, but
# aiohttp 3.9.x exposes ClientConnectorError instead. Provide a compatibility
# alias before importing google.genai so Gemini requests can still run.
if not hasattr(aiohttp, "ClientConnectorDNSError"):
    aiohttp.ClientConnectorDNSError = aiohttp.ClientConnectorError  # type: ignore[attr-defined]

from google import genai
from google.genai import types

from core.config import settings
from services.circuit_breaker import CircuitBreaker

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

ROOT_DIRECTORY = Path(__file__).resolve().parent.parent


class AIProvider(str, Enum):
    GEMINI = "gemini"
    # Not user-selectable via the API (routers still validate ai_provider
    # == "gemini" on incoming requests) — this is purely the internal
    # fallback target when Gemini is failing. See get_caption_generator().
    ANTHROPIC = "anthropic"


# ── Schemas ───────────────────────────────────────────────────────────────────

class MemeOutput(BaseModel):
    meme_id: int = Field(description="The integer ID of the template from the provided list")
    meme_name: str = Field(description="The name of the template")
    meme_text: List[str] = Field(description="The captions to place on the meme")
    reasoning: str = Field(description="One sentence explaining why this template fits the prompt")


class MemeList(BaseModel):
    output: List[MemeOutput] = Field(description="Generated meme options")


# ── Clients ───────────────────────────────────────────────────────────────────
gemini_client = genai.Client(
    api_key=settings.gemini_api_key
) if settings.gemini_api_key else None

try:
    import anthropic
    anthropic_api_key = settings.anthropic_api_key.strip()
    if anthropic_api_key and settings.has_valid_anthropic_key:
        anthropic_client: Optional["anthropic.AsyncAnthropic"] = anthropic.AsyncAnthropic(api_key=anthropic_api_key)
    else:
        anthropic_client = None
        if anthropic_api_key:
            logger.warning(
                "Anthropic API key is present but does not look valid; skipping client initialization"
            )
except ImportError:
    anthropic = None  # type: ignore
    anthropic_client = None

# Trips after 3 consecutive Gemini failures, stays open for 30s before
# allowing a single recovery probe. Process-local — see CircuitBreaker docstring.
_gemini_circuit = CircuitBreaker(failure_threshold=3, recovery_timeout_seconds=30.0)


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

def _build_gemini_system(meme_data: str, option_count: int = 3) -> str:
    option_text = "1 meme option" if option_count == 1 else f"{option_count} different meme options"
    return f"""You are a Gen-Z meme genius who creates hilarious, relatable memes.

{_GEN_Z_CONTEXT}

Available templates: {meme_data}

Rules:
- Choose {option_text} that best fit the user's prompt
- **CRITICAL**: Follow the EXACT ORDER specified in usage_instructions for each template
- Text must be SHORT (max 10 words per field) and punchy
- Match the exact number of text fields per template
- Provide exactly {option_count} meme option{"s" if option_count != 1 else ""} with proper structure"""


def _build_anthropic_system(meme_data: str, option_count: int = 3) -> str:
    option_text = "1 meme option" if option_count == 1 else f"{option_count} different meme options"
    return f"""You are a Gen-Z meme genius who creates hilarious, relatable memes.

{_GEN_Z_CONTEXT}

Available templates: {meme_data}

Rules:
- Choose {option_text} that best fit the user's prompt
- **CRITICAL**: Follow the EXACT ORDER specified in usage_instructions for each template
- Text must be SHORT (max 10 words per field) and punchy
- Match the exact number of text fields per template
- Provide exactly {option_count} meme option{"s" if option_count != 1 else ""}

Respond with ONLY a raw JSON object of this exact shape, no markdown fences, no commentary:
{{"output": [{{"meme_id": <int>, "meme_name": "<string>", "meme_text": ["<string>", ...], "reasoning": "<string>"}}]}}"""


# ── Gemini ────────────────────────────────────────────────────────────────────

async def generate_meme_captions_with_gemini(
    prompt: str,
    option_count: int = 3,
) -> Optional[List[Dict[str, Any]]]:
    if not gemini_client:
        logger.warning("Gemini client not configured")
        return None

    meme_data = load_meme_data()
    try:
        # Phase 2: tightened from BLOCK_ONLY_HIGH (the most permissive tier)
        # to BLOCK_MEDIUM_AND_ABOVE on every category. This still allows
        # raunchy/edgy meme humor through but no longer waves through
        # medium-severity content with nothing downstream reviewing it.
        # services/moderation.py adds a second, independent check on top of
        # this for anything that does get through.
        safety_settings = [
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_MEDIUM_AND_ABOVE"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
        ]

        config = types.GenerateContentConfig(
            system_instruction=_build_gemini_system(meme_data, option_count),
            max_output_tokens=1536 if option_count == 1 else 4096,
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
                
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError as json_err:
                    # Try to recover from incomplete JSON by finding the last complete meme
                    logger.warning("Failed to parse JSON on attempt %d: %s. Attempting recovery...", attempt + 1, json_err)
                    # Find the last complete meme object by looking for the last closing brace
                    last_brace = raw.rfind('},')
                    if last_brace > 0:
                        recovered = raw[:last_brace + 1] + ']\n}'
                        try:
                            data = json.loads(recovered)
                            logger.info("Successfully recovered partial JSON response")
                        except json.JSONDecodeError:
                            if attempt < max_retries:
                                logger.info("Recovery failed, retrying (attempt %d of %d)...", attempt + 2, max_retries + 1)
                                continue
                            raise
                    else:
                        if attempt < max_retries:
                            logger.info("Could not recover incomplete JSON, retrying (attempt %d of %d)...", attempt + 2, max_retries + 1)
                            continue
                        raise
                
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
                return valid_memes[:option_count]
                
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


# ── Anthropic (Phase 2 — Gemini fallback) ─────────────────────────────────────

async def generate_meme_captions_with_anthropic(
    prompt: str,
    option_count: int = 3,
) -> Optional[List[Dict[str, Any]]]:
    """
    Fallback caption generator. Same contract/return shape as the Gemini
    function above. Invoked automatically by get_caption_generator() when
    Gemini is failing or its circuit breaker is open — not selected by
    default otherwise, since Gemini remains the cheaper/primary provider
    for this workload.
    """
    if not anthropic_client:
        logger.warning("Anthropic client not configured (ANTHROPIC_API_KEY missing) — cannot fall back")
        return None

    meme_data = load_meme_data()
    try:
        resp = await anthropic_client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1536 if option_count == 1 else 4096,
            system=_build_anthropic_system(meme_data, option_count),
            messages=[{"role": "user", "content": prompt}],
        )

        raw = "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        ).strip()

        if not raw:
            logger.error("Anthropic fallback returned an empty response")
            return None

        # Defensive: strip accidental markdown fences even though the
        # system prompt asks for raw JSON.
        if raw.startswith("```"):
            raw = raw.strip("`").strip()
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as json_err:
            logger.warning("Failed to parse Anthropic JSON: %s. Attempting recovery...", json_err)
            last_brace = raw.rfind("},")
            if last_brace > 0:
                data = json.loads(raw[: last_brace + 1] + "]\n}")
            else:
                raise

        output = data.get("output", []) if isinstance(data, dict) else data
        if not output or not isinstance(output, list):
            logger.error("Anthropic fallback returned empty/invalid output array")
            return None

        valid_memes: List[Dict[str, Any]] = []
        for meme in output:
            if not isinstance(meme, dict):
                continue
            meme_id = meme.get("meme_id") or meme.get("id")
            meme_name = meme.get("meme_name") or meme.get("name")
            meme_text = meme.get("meme_text") or meme.get("text")
            if meme_id is None or not meme_name or not meme_text:
                logger.warning("Skipping incomplete meme object from Anthropic: %s", meme)
                continue
            valid_memes.append({
                "meme_id": int(meme_id),
                "meme_name": str(meme_name),
                "meme_text": list(meme_text) if isinstance(meme_text, list) else [str(meme_text)],
                "reasoning": meme.get("reasoning", "Generated by Anthropic (Gemini fallback)"),
            })

        if not valid_memes:
            logger.error("No valid memes parsed from Anthropic fallback response")
            return None

        logger.info("Anthropic fallback generated %d valid memes", len(valid_memes))
        return valid_memes[:option_count]

    except Exception as exc:
        logger.exception("Anthropic fallback caption generation failed: %s", exc)
        return None


# ── Factory ───────────────────────────────────────────────────────────────────

async def get_caption_generator(provider: Optional[str] = None, option_count: int = 3):
    """
    Return a caption generator with automatic Gemini -> Anthropic fallback.

    Phase 2 remediation: previously a single Gemini outage (or quota
    exhaustion) took down 100% of generation despite ANTHROPIC_API_KEY
    being configured in every env file from the start. This wraps Gemini
    with a circuit breaker (services/circuit_breaker.py) and transparently
    falls back to Anthropic — if configured — when Gemini is failing or its
    breaker is open. Callers don't need to know which provider actually
    served a given request; `reasoning` in the returned dict says so if
    you need to check.
    """

    async def robust_generator(prompt: str) -> Optional[List[Dict[str, Any]]]:
        if settings.has_gemini and await _gemini_circuit.allow_request():
            try:
                result = await asyncio.wait_for(
                    generate_meme_captions_with_gemini(prompt, option_count=option_count),
                    timeout=20.0,
                )
            except asyncio.TimeoutError:
                logger.error("Gemini caption generation timed out after 20 seconds")
                result = None
            except Exception as exc:
                logger.error("Gemini caption generation failed: %s", exc)
                result = None

            if result:
                await _gemini_circuit.record_success()
                return result

            await _gemini_circuit.record_failure()
            logger.warning(
                "Gemini failed (circuit breaker state=%s) — falling back to Anthropic",
                _gemini_circuit.state.value,
            )
        elif settings.has_gemini:
            logger.warning("Gemini circuit breaker is OPEN — skipping straight to Anthropic fallback")

        if not settings.has_anthropic:
            logger.error("No fallback provider configured (ANTHROPIC_API_KEY missing) — generation failed")
            return None

        try:
            return await asyncio.wait_for(
                generate_meme_captions_with_anthropic(prompt, option_count=option_count),
                timeout=20.0,
            )
        except asyncio.TimeoutError:
            logger.error("Anthropic fallback timed out after 20 seconds")
            return None
        except Exception as exc:
            logger.error("Anthropic fallback failed: %s", exc)
            return None

    return robust_generator


