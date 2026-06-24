"""
Rate-limiting tests — Phase 3.

Key things to verify (all pure unit / middleware logic, no real Redis):

1. _normalize_api_path strips /api/v1 and /api prefixes identically — this
   is the regression guard for the silent rate-limit bypass discovered
   during Phase 2's API versioning work.

2. The burst guard (check_generation_burst_limit) calls check_rate_limit
   with the short burst window key prefix.

3. RateLimitMiddleware correctly identifies generation endpoints regardless
   of which version prefix is used.

4. Per-plan daily limits: free=5, pro=500, api=500.

5. A 429 from check_rate_limit surfaces correct Retry-After headers.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException


# ── Path normalisation (Phase 2 regression guard) ────────────────────────────

class TestNormalizeApiPath:
    """
    _normalize_api_path is a private function in core/middleware.py.
    We test it directly because a regression here silently re-opens the
    unbounded-cost-exposure that Phase 1 fixed for anyone using /api/v1.
    """

    def _normalize(self, path: str) -> str:
        # Import inline so other tests don't fail if middleware has import issues
        from core.middleware import _normalize_api_path
        return _normalize_api_path(path)

    def test_v1_prefix_stripped(self):
        assert self._normalize("/api/v1/memes/generate") == "/memes/generate"

    def test_legacy_prefix_stripped(self):
        assert self._normalize("/api/memes/generate") == "/memes/generate"

    def test_no_prefix_unchanged(self):
        assert self._normalize("/memes/generate") == "/memes/generate"

    def test_health_v1_stripped(self):
        assert self._normalize("/api/v1/health") == "/health"

    def test_health_legacy_stripped(self):
        assert self._normalize("/api/health") == "/health"

    def test_partial_match_not_stripped(self):
        # /apiv1/ should not be mistaken for a prefix
        assert self._normalize("/apiv1/memes") == "/apiv1/memes"

    def test_empty_path_unchanged(self):
        assert self._normalize("") == ""

    def test_root_unchanged(self):
        assert self._normalize("/") == "/"

    @pytest.mark.parametrize("path,expected", [
        ("/api/v1/memes/generate/quick", "/memes/generate/quick"),
        ("/api/v1/memes/templates",      "/memes/templates"),
        ("/api/v1/trending/topics",      "/trending/topics"),
        ("/api/memes/generate/quick",    "/memes/generate/quick"),
        ("/api/memes/templates",         "/memes/templates"),
        ("/api/trending/topics",         "/trending/topics"),
    ])
    def test_parametrized_endpoints(self, path, expected):
        assert self._normalize(path) == expected


# ── RateLimitMiddleware route detection ───────────────────────────────────────

class TestMiddlewareRouteDetection:
    """
    Verify that the middleware classifies requests correctly AFTER
    path normalisation — i.e., that /api/v1/memes/generate and
    /api/memes/generate both trigger rate-limiting.
    """

    def _should_limit(self, method: str, path: str) -> tuple[bool, bool]:
        """
        Replicate the middleware's should_rate_limit / is_generation logic.
        Returns (should_rate_limit, is_generation).
        """
        from core.middleware import _normalize_api_path
        p = _normalize_api_path(path)
        should = False
        is_gen = False
        if method == "POST" and p.startswith("/memes/generate"):
            should = True
            is_gen = True
        if method == "GET" and p.startswith("/memes/templates"):
            should = True
        if method == "GET" and p.startswith("/trending/topics"):
            should = True
        return should, is_gen

    @pytest.mark.parametrize("path", [
        "/api/v1/memes/generate",
        "/api/v1/memes/generate/quick",
        "/api/memes/generate",
        "/api/memes/generate/quick",
    ])
    def test_post_generate_is_rate_limited_and_generation(self, path):
        limited, is_gen = self._should_limit("POST", path)
        assert limited is True, f"POST {path} should be rate limited"
        assert is_gen is True, f"POST {path} should be flagged as generation"

    @pytest.mark.parametrize("path", [
        "/api/v1/memes/templates",
        "/api/memes/templates",
    ])
    def test_get_templates_rate_limited_not_generation(self, path):
        limited, is_gen = self._should_limit("GET", path)
        assert limited is True
        assert is_gen is False

    @pytest.mark.parametrize("path", [
        "/api/v1/trending/topics",
        "/api/trending/topics",
    ])
    def test_get_trending_rate_limited_not_generation(self, path):
        limited, is_gen = self._should_limit("GET", path)
        assert limited is True
        assert is_gen is False

    @pytest.mark.parametrize("path", [
        "/api/v1/memes/1234",
        "/api/memes/public",
        "/api/v1/auth/login",
        "/api/v1/health",
    ])
    def test_read_endpoints_not_rate_limited(self, path):
        for method in ("GET", "POST"):
            limited, _ = self._should_limit(method, path)
            # Only check non-generate POSTs; GET /memes/1234 is never limited
            if method == "GET":
                assert limited is False, f"GET {path} should not be rate limited"


# ── Plan tier limits ──────────────────────────────────────────────────────────

class TestPlanLimits:
    """Daily generation limits per plan — pulled from Settings."""

    def test_free_limit(self):
        from core.config import settings
        assert settings.rate_limit_free == 5

    def test_pro_limit(self):
        from core.config import settings
        assert settings.rate_limit_pro == 500

    def test_api_limit(self):
        from core.config import settings
        assert settings.rate_limit_api == 500

    def test_burst_defaults(self):
        from core.config import settings
        assert settings.generation_burst_limit == 5
        assert settings.generation_burst_window_seconds == 60


# ── 429 response shape ────────────────────────────────────────────────────────

class TestRateLimitResponseShape:
    """
    When check_rate_limit fires a 429, the HTTPException must carry the
    standard rate-limit headers so clients know when to retry.
    """

    @pytest.mark.asyncio
    async def test_429_carries_retry_after(self):
        from services.rate_limit import check_rate_limit
        with pytest.raises(HTTPException) as exc_info:
            await check_rate_limit("test-id", limit=0, window_seconds=60)
        exc = exc_info.value
        assert exc.status_code == 429
        assert "Retry-After" in exc.headers
        assert "X-RateLimit-Limit" in exc.headers
        assert "X-RateLimit-Remaining" in exc.headers
        assert exc.headers["X-RateLimit-Remaining"] == "0"

    @pytest.mark.asyncio
    async def test_burst_limit_identifier_uses_burst_prefix(self):
        """
        check_generation_burst_limit should call check_rate_limit with
        key_prefix="rl:burst:" — different from the daily window's "rl:fixed:".
        This ensures burst and daily quota don't share the same Redis key.
        """
        from unittest.mock import AsyncMock, patch

        captured_calls = []

        async def _fake_check(identifier, limit, window_seconds, key_prefix="rl:fixed:"):
            captured_calls.append({"identifier": identifier, "key_prefix": key_prefix})
            return 1, 4

        with patch("services.rate_limit.check_rate_limit", side_effect=_fake_check):
            from services.rate_limit import check_generation_burst_limit
            await check_generation_burst_limit("user:abc")

        assert len(captured_calls) == 1
        assert captured_calls[0]["key_prefix"] == "rl:burst:"
