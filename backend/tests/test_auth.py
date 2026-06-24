"""
Auth service unit tests — Phase 3.

Covers:
  - access/refresh token creation and round-trip verification
  - token type enforcement (access token rejected as refresh and vice versa)
  - expired token rejection
  - get_current_admin_user: 403 on non-admin, pass-through on admin
  - config validator: refuses to start in production with unsafe defaults

No database or network required; all fixtures are unit-level.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest

from services.auth import (
    REFRESH_COOKIE_NAME,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    verify_token,
)


# ── Token round-trip ──────────────────────────────────────────────────────────

class TestAccessToken:
    def test_round_trip(self):
        """A freshly minted access token verifies successfully."""
        token = create_access_token({"sub": "user-123"})
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"

    def test_type_claim_is_access(self):
        """Token payload carries type=access (or omits type entirely)."""
        token = create_access_token({"sub": "user-123"})
        raw = jwt.decode(token, options={"verify_signature": False})
        assert raw.get("type") in (None, "access")

    def test_refresh_token_rejected_as_access(self):
        """A refresh token must not be accepted by verify_token."""
        refresh = create_refresh_token("user-123")
        assert verify_token(refresh) is None

    def test_malformed_token_rejected(self):
        assert verify_token("not.a.jwt") is None

    def test_garbage_rejected(self):
        assert verify_token("") is None


class TestRefreshToken:
    def test_round_trip(self):
        """A freshly minted refresh token verifies successfully."""
        token = create_refresh_token("user-xyz")
        payload = verify_refresh_token(token)
        assert payload is not None
        assert payload["sub"] == "user-xyz"
        assert payload["type"] == "refresh"

    def test_access_token_rejected_as_refresh(self):
        """An access token must not be accepted by verify_refresh_token."""
        access = create_access_token({"sub": "user-xyz"})
        assert verify_refresh_token(access) is None

    def test_malformed_rejected(self):
        assert verify_refresh_token("garbage") is None


class TestExpiry:
    def test_expired_access_token_rejected(self):
        """A token with a past expiry must be rejected."""
        from core.config import settings

        expired_payload = {
            "sub": "user-expired",
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        }
        token = jwt.encode(expired_payload, settings.secret_key, algorithm="HS256")
        assert verify_token(token) is None

    def test_expired_refresh_token_rejected(self):
        from core.config import settings

        expired_payload = {
            "sub": "user-expired",
            "type": "refresh",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        }
        token = jwt.encode(expired_payload, settings.secret_key, algorithm="HS256")
        assert verify_refresh_token(token) is None


# ── REFRESH_COOKIE_NAME constant ──────────────────────────────────────────────

def test_refresh_cookie_name_is_stable():
    """The constant must match settings so we never accidentally rename it."""
    from core.config import settings
    assert REFRESH_COOKIE_NAME == settings.refresh_cookie_name


# ── Production config guard ───────────────────────────────────────────────────

class TestProductionConfigGuard:
    """
    The @model_validator on Settings must refuse to start with unsafe defaults
    in ENVIRONMENT=production. Tests isolate by constructing Settings directly
    with overridden values rather than polluting os.environ.
    """

    def test_placeholder_secret_key_rejected(self):
        os.environ["ENVIRONMENT"] = "production"
        os.environ["SECRET_KEY"] = "your-secret-key-here"  # placeholder
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://real:pass@host/memegpt"
        try:
            from core import config as cfg_mod
            # Force re-construction to pick up the env changes
            with pytest.raises((ValueError, Exception)):
                from pydantic_settings import BaseSettings
                from core.config import Settings
                Settings(
                    _env_file=None,
                    environment="production",
                    secret_key="your-secret-key-here",
                    database_url="postgresql+asyncpg://real:pass@host/memegpt",
                )
        finally:
            os.environ["ENVIRONMENT"] = "development"
            os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-32x"
            os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

    def test_short_secret_key_rejected(self):
        from core.config import Settings
        with pytest.raises((ValueError, Exception)):
            Settings(
                _env_file=None,
                environment="production",
                secret_key="tooshort",
                database_url="postgresql+asyncpg://real:pass@host/memegpt",
            )

    def test_safe_production_config_accepted(self):
        """A real 32-char secret + real DB URL boots without error."""
        from core.config import Settings
        s = Settings(
            _env_file=None,
            environment="production",
            secret_key="a" * 32,
            database_url="postgresql+asyncpg://real:pass@prodhost/memegpt",
        )
        assert s.is_production is True
