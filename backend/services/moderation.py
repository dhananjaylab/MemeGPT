"""
Lightweight content moderation for AI-generated meme captions.

Phase 2 remediation: previously every AI-generated meme went straight to
the public gallery (`is_public=True`, no review) the moment generation
succeeded, with Gemini's own safety thresholds deliberately set to their
most permissive tier ("to be more permissive for meme humor"). This module
adds a second, independent check before anything is marked public:

  1. Gemini's safety thresholds were tightened separately (see
     services/meme_ai.py) — that's the first line of defense, upstream of
     this module.
  2. This module sends the generated caption text through a dedicated
     classification call (reusing whichever provider is configured —
     Gemini preferred, Anthropic as fallback, since this is a cheap
     classification call, not a generation call) asking a structured
     yes/no "is this OK for a public, general-audience meme gallery"
     question.

Anything that fails is stored with moderation_status="flagged" and
is_public=False — still visible to its own creator, hidden from /gallery,
and surfaced in the admin review queue
(GET /api/memes/moderation/flagged, admin-only).

This is NOT a substitute for a production-grade moderation vendor — it's
the minimum defensible bar of "nothing unreviewed reaches a public surface
automatically." Phase 3 should evaluate a dedicated moderation API
(e.g. a hosted moderation endpoint) if generation volume grows.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import List, Optional

from core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ModerationResult:
    approved: bool
    reason: str
    provider: str  # "gemini" | "anthropic" | "none" (disabled/unavailable)


_MODERATION_SYSTEM_PROMPT = """You are a content moderator for a public, ad-supported meme-generation website with a general audience that includes teenagers.

You will be shown the caption text for one generated meme (multiple text fields joined by " | "). Respond with ONLY a raw JSON object, no markdown fences, no commentary:
{"approved": true or false, "reason": "<one short sentence>"}

Reject (approved=false) if the text contains any of: sexual content, slurs or hate speech, harassment or bullying targeting a real identifiable person or a protected group, glorification of violence or self-harm, or content otherwise inappropriate for a general/teen audience.

Mild crude humor, sarcasm, and profanity-free edgy jokes are fine — this is a meme site, not a children's app. When genuinely unsure between "edgy but fine" and "actually harmful", reject and explain why briefly."""


def _parse_json_response(raw: str) -> Optional[dict]:
    """Parse a model response that is supposed to be JSON.

    We accept small amounts of damage from providers that emit extra prose
    or truncated JSON, then fall back to the next provider.
    """
    candidate = raw.strip()
    if not candidate:
        return None

    if candidate.startswith("```"):
        candidate = candidate.strip("`").strip()
        if candidate.lower().startswith("json"):
            candidate = candidate[4:].strip()

    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    for end in range(len(candidate), 0, -1):
        if candidate[end - 1] not in "}]":
            continue
        fragment = candidate[:end]
        try:
            parsed = json.loads(fragment)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            continue

    return None


async def _classify(captions: List[str]) -> Optional[ModerationResult]:
    """Run the structured moderation classification call. Returns None if
    no provider is available/reachable (caller decides fail-open vs
    fail-closed in that case — see moderate_captions)."""
    joined = " | ".join(t.strip() for t in captions if t and t.strip())
    if not joined:
        return ModerationResult(approved=True, reason="No text to moderate", provider="none")

    # Local import: avoids a hard circular-import dependency at module load
    # time (meme_ai imports nothing from here), and means this module works
    # even if meme_ai's Gemini/Anthropic clients fail to construct.
    from services.meme_ai import gemini_client, anthropic_client

    if gemini_client:
        try:
            from google.genai import types as genai_types

            resp = await gemini_client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=joined,
                config=genai_types.GenerateContentConfig(
                    system_instruction=_MODERATION_SYSTEM_PROMPT,
                    max_output_tokens=200,
                    temperature=0,
                    response_mime_type="application/json",
                ),
            )
            raw = "".join(
                part.text for part in resp.candidates[0].content.parts if getattr(part, "text", None)
            ).strip()
            data = _parse_json_response(raw)
            if data is not None:
                return ModerationResult(
                    approved=bool(data.get("approved", False)),
                    reason=str(data.get("reason", "")),
                    provider="gemini",
                )
            logger.warning("Gemini moderation returned unparseable JSON; trying Anthropic")
        except Exception as exc:
            logger.warning("Gemini moderation classification failed; trying Anthropic: %s", exc)

    if anthropic_client:
        try:
            resp = await anthropic_client.messages.create(
                model=settings.anthropic_model,
                max_tokens=200,
                system=_MODERATION_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": joined}],
            )
            raw = "".join(
                block.text for block in resp.content if getattr(block, "type", None) == "text"
            ).strip()
            data = _parse_json_response(raw)
            if data is not None:
                return ModerationResult(
                    approved=bool(data.get("approved", False)),
                    reason=str(data.get("reason", "")),
                    provider="anthropic",
                )
            logger.warning("Anthropic moderation returned unparseable JSON")
        except Exception as exc:
            logger.warning("Anthropic moderation classification failed: %s", exc)

    return None


async def moderate_captions(captions: List[str]) -> ModerationResult:
    """
    The single entry point the generation pipeline should call before
    setting is_public=True on a GeneratedMeme. See module docstring for
    the full design rationale.
    """
    if not settings.moderation_enabled:
        return ModerationResult(approved=True, reason="Moderation disabled via settings", provider="none")

    result = await _classify(captions)
    if result is not None:
        if not result.approved:
            logger.info("Caption flagged by moderation (%s): %s", result.provider, result.reason)
        return result

    # Both moderation-capable providers were unreachable/unconfigured.
    if settings.moderation_fail_closed:
        logger.error("Moderation provider unavailable — failing CLOSED (MODERATION_FAIL_CLOSED=true)")
        return ModerationResult(
            approved=False,
            reason="Moderation provider unavailable",
            provider="none",
        )

    logger.warning(
        "Moderation provider unavailable — approving by default (fail-open). "
        "Set MODERATION_FAIL_CLOSED=true to change this once you've measured how often it happens."
    )
    return ModerationResult(
        approved=True,
        reason="Moderation provider unavailable — fail-open default",
        provider="none",
    )


