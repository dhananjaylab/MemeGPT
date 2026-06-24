"""
Content moderation tests — Phase 3.

Covers:
  - moderate_captions is skipped (approved=True) when MODERATION_ENABLED=False
  - fail-open default: when _classify returns None, content is approved
  - fail-closed mode: when _classify returns None, content is flagged
  - approved classification is correctly reflected in ModerationResult
  - flagged classification is correctly reflected in ModerationResult
  - empty captions list → approved immediately without any provider call
  - GeneratedMeme gets correct moderation_status / is_public values depending
    on moderation outcome (tested via the model, not via HTTP to avoid the
    full stack)
  - circuit_breaker state machine: CLOSED → OPEN after threshold,
    OPEN → HALF_OPEN after recovery window
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

import pytest

from services.circuit_breaker import CircuitBreaker, CircuitState
from services.moderation import ModerationResult, moderate_captions


# ── moderate_captions: disabled path ────────────────────────────────────────

@pytest.mark.asyncio
async def test_moderation_disabled_approves_everything(monkeypatch):
    """When MODERATION_ENABLED=false, we skip the classification call entirely."""
    monkeypatch.setattr("services.moderation.settings.moderation_enabled", False)

    result = await moderate_captions(["whatever text", "doesn't matter"])

    assert result.approved is True
    assert result.provider == "none"


@pytest.mark.asyncio
async def test_moderation_disabled_skips_provider_call(monkeypatch):
    monkeypatch.setattr("services.moderation.settings.moderation_enabled", False)

    mock_classify = AsyncMock()
    with patch("services.moderation._classify", mock_classify):
        await moderate_captions(["text"])

    mock_classify.assert_not_called()


# ── _classify paths ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fail_open_when_classify_returns_none(monkeypatch):
    """Default (fail-open): provider unavailable → content approved."""
    monkeypatch.setattr("services.moderation.settings.moderation_enabled", True)
    monkeypatch.setattr("services.moderation.settings.moderation_fail_closed", False)

    with patch("services.moderation._classify", AsyncMock(return_value=None)):
        result = await moderate_captions(["some caption"])

    assert result.approved is True
    assert "fail-open" in result.reason


@pytest.mark.asyncio
async def test_fail_closed_when_classify_returns_none(monkeypatch):
    """When MODERATION_FAIL_CLOSED=true and provider is down → content flagged."""
    monkeypatch.setattr("services.moderation.settings.moderation_enabled", True)
    monkeypatch.setattr("services.moderation.settings.moderation_fail_closed", True)

    with patch("services.moderation._classify", AsyncMock(return_value=None)):
        result = await moderate_captions(["some caption"])

    assert result.approved is False
    assert result.provider == "none"


@pytest.mark.asyncio
async def test_approved_classification_propagated(monkeypatch):
    monkeypatch.setattr("services.moderation.settings.moderation_enabled", True)

    good = ModerationResult(approved=True, reason="Looks fine", provider="gemini")
    with patch("services.moderation._classify", AsyncMock(return_value=good)):
        result = await moderate_captions(["wholesome text"])

    assert result.approved is True
    assert result.reason == "Looks fine"
    assert result.provider == "gemini"


@pytest.mark.asyncio
async def test_flagged_classification_propagated(monkeypatch):
    monkeypatch.setattr("services.moderation.settings.moderation_enabled", True)

    bad = ModerationResult(approved=False, reason="Contains slur", provider="anthropic")
    with patch("services.moderation._classify", AsyncMock(return_value=bad)):
        result = await moderate_captions(["offensive caption"])

    assert result.approved is False
    assert result.reason == "Contains slur"
    assert result.provider == "anthropic"


# ── Empty captions ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_empty_captions_approved_without_provider(monkeypatch):
    """
    An empty caption list short-circuits to approved inside _classify itself
    (the joined text is empty so there is nothing to moderate) — no AI
    provider is contacted.
    """
    monkeypatch.setattr("services.moderation.settings.moderation_enabled", True)

    # Do NOT patch _classify — the real implementation returns an immediate
    # ModerationResult(approved=True, reason="No text to moderate") for
    # empty joined text without calling any provider.
    result = await moderate_captions([])

    assert result.approved is True


# ── ModerationResult → GeneratedMeme field mapping ───────────────────────────

class TestModerationResultModelMapping:
    """
    Verify the mapping convention between ModerationResult and the fields
    written to GeneratedMeme — not via HTTP, just the model logic.
    """

    def _fields_for(self, approved: bool, reason: str) -> dict:
        """Replicate the mapping from workers/meme_worker.py _compose_one_meme."""
        mod = ModerationResult(approved=approved, reason=reason, provider="gemini")
        return {
            "is_public": mod.approved,
            "moderation_status": "approved" if mod.approved else "flagged",
            "moderation_reason": mod.reason or None,
        }

    def test_approved_sets_is_public_true(self):
        fields = self._fields_for(True, "Looks good")
        assert fields["is_public"] is True
        assert fields["moderation_status"] == "approved"

    def test_flagged_sets_is_public_false(self):
        fields = self._fields_for(False, "Contains slur")
        assert fields["is_public"] is False
        assert fields["moderation_status"] == "flagged"

    def test_empty_reason_stored_as_none(self):
        fields = self._fields_for(True, "")
        assert fields["moderation_reason"] is None


# ── Circuit breaker state machine ─────────────────────────────────────────────

class TestCircuitBreaker:
    """
    The circuit breaker (services/circuit_breaker.py) is the mechanism that
    stops hammering a failing AI provider and triggers the fallback.
    This tests the state machine in isolation.
    """

    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout_seconds=30)
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_allows_requests_when_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        assert await cb.allow_request() is True

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            await cb.record_failure()
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_blocks_requests(self):
        cb = CircuitBreaker(failure_threshold=1)
        await cb.record_failure()
        assert await cb.allow_request() is False

    @pytest.mark.asyncio
    async def test_success_resets_to_closed(self):
        cb = CircuitBreaker(failure_threshold=1)
        await cb.record_failure()
        assert cb.state == CircuitState.OPEN
        # Simulate recovery window passing
        cb._opened_at = time.monotonic() - 31
        # Allow one probe
        assert await cb.allow_request() is True
        await cb.record_success()
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_after_recovery_window(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout_seconds=0.05)
        await cb.record_failure()
        await asyncio.sleep(0.1)  # wait for recovery window
        # Next request should be allowed (probe)
        assert await cb.allow_request() is True
        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_failure_returns_to_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout_seconds=0.05)
        await cb.record_failure()
        await asyncio.sleep(0.1)
        await cb.allow_request()  # transitions to HALF_OPEN
        await cb.record_failure()  # probe failed
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_failure_below_threshold_stays_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        await cb.record_failure()
        await cb.record_failure()
        # Still one below threshold
        assert cb.state == CircuitState.CLOSED
        assert await cb.allow_request() is True
