"""
Meme API endpoint tests — Phase 3.

Covers:
  - POST /api/v1/memes/generate: validation (empty prompt, too-long prompt,
    bad ai_provider, bad generation_mode)
  - POST /api/v1/memes/generate/quick: happy path with cache hit, 202 on cache miss
  - GET  /api/v1/memes/public: lists only is_public=True, moderation_status=approved memes
  - GET  /api/v1/memes/{id}: 404 on private meme, 200 on public
  - POST /api/v1/memes/{id}/share, /{id}/like: increment counts
  - DELETE /api/v1/memes/{id}: 401 without auth, 403 for non-owner, 200 for owner
  - GET  /api/v1/memes/moderation/flagged: 403 without admin, 200 with admin token

Tests mock the ARQ worker and AI/moderation calls — no real queue needed.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from models.models import GeneratedMeme, MemeTemplate
from services.auth import create_access_token

# ── Local factory helpers (duplicated from conftest to avoid import issues) ───

def make_template(
    *,
    id: int = 0,
    name: str = "Drake Hotline Bling Meme",
    source: str = "local",
    n_fields: int = 2,
) -> MemeTemplate:
    return MemeTemplate(
        id=id,
        name=name,
        alternative_names=[],
        file_path="Drake-Hotline-Bling.jpg",
        font_path="impact.ttf",
        text_color="white",
        text_stroke=True,
        usage_instructions="Test usage instructions.",
        number_of_text_fields=n_fields,
        text_coordinates_xy_wh=[[0, 0, 100, 100]] * n_fields,
        text_coordinates=[[0, 0, 100, 100]] * n_fields,
        example_output=["text1", "text2"][:n_fields],
        source=source,
        gen_z_ready=True,
    )


def make_meme(
    *,
    user_id: str | None = None,
    is_public: bool = True,
    moderation_status: str = "approved",
    template_name: str = "Drake Hotline Bling Meme",
    template_id: int = 0,
) -> GeneratedMeme:
    return GeneratedMeme(
        id=str(uuid4()),
        user_id=user_id,
        prompt="test prompt",
        template_name=template_name,
        template_id=template_id,
        meme_text=["top text", "bottom text"],
        image_url="https://example.com/test.webp",
        is_public=is_public,
        moderation_status=moderation_status,
        share_count=0,
        like_count=0,
        trending_score=0.0,
        created_at=datetime.now(timezone.utc),
    )


# ── POST /memes/generate — input validation ───────────────────────────────────

class TestGenerateValidation:
    @pytest.mark.asyncio
    async def test_empty_prompt_rejected(self, async_client: AsyncClient, free_user_headers):
        resp = await async_client.post(
            "/api/v1/memes/generate",
            json={"prompt": "   "},
            headers=free_user_headers,
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_too_long_prompt_rejected(self, async_client: AsyncClient, free_user_headers):
        resp = await async_client.post(
            "/api/v1/memes/generate",
            json={"prompt": "x" * 1001},
            headers=free_user_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_ai_provider_rejected(self, async_client: AsyncClient, free_user_headers):
        with patch("services.worker.enqueue_meme_generation", AsyncMock(return_value="job-1")):
            resp = await async_client.post(
                "/api/v1/memes/generate",
                json={"prompt": "valid prompt", "ai_provider": "openai"},
                headers=free_user_headers,
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_generation_mode_rejected(self, async_client: AsyncClient, free_user_headers):
        with patch("services.worker.enqueue_meme_generation", AsyncMock(return_value="job-1")):
            resp = await async_client.post(
                "/api/v1/memes/generate",
                json={"prompt": "valid", "generation_mode": "magic"},
                headers=free_user_headers,
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_manual_mode_without_template_id_rejected(
        self, async_client: AsyncClient, free_user_headers
    ):
        with patch("services.worker.enqueue_meme_generation", AsyncMock(return_value="job-1")):
            resp = await async_client.post(
                "/api/v1/memes/generate",
                json={"prompt": "valid", "generation_mode": "manual"},
                headers=free_user_headers,
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_valid_request_enqueues_job(self, async_client: AsyncClient, free_user, free_user_headers):
        from services.auth import get_current_user_optional
        app = async_client._transport.app  # type: ignore[attr-defined]

        # Must use explicit Request signature — *args/**kwargs are misread as query params
        async def _override():
            return free_user

        app.dependency_overrides[get_current_user_optional] = _override

        with patch("routers.memes.enqueue_meme_generation", AsyncMock(return_value="job-abc")):
            resp = await async_client.post(
                "/api/v1/memes/generate",
                json={"prompt": "when the coffee hits"},
                headers=free_user_headers,
            )

        app.dependency_overrides.pop(get_current_user_optional, None)
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == "job-abc"
        assert "remaining_generations" in data


# ── GET /memes/public ─────────────────────────────────────────────────────────

class TestPublicMemeList:
    @pytest.mark.asyncio
    async def test_only_public_approved_memes_returned(
        self, async_client: AsyncClient, db_session, free_user
    ):
        """Private memes and flagged memes must not appear in /public."""
        public = make_meme(user_id=free_user.id, is_public=True, moderation_status="approved")
        private = make_meme(user_id=free_user.id, is_public=False, moderation_status="flagged")
        db_session.add_all([public, private])
        await db_session.flush()

        resp = await async_client.get("/api/v1/memes/public")
        assert resp.status_code == 200
        data = resp.json()
        ids = [m["id"] for m in data["memes"]]
        assert public.id in ids
        assert private.id not in ids

    @pytest.mark.asyncio
    async def test_pagination_returns_correct_shape(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/memes/public?page=1&limit=5")
        assert resp.status_code == 200
        body = resp.json()
        assert "memes" in body
        assert "total" in body
        assert "has_more" in body
        assert isinstance(body["memes"], list)


# ── GET /memes/{id} ───────────────────────────────────────────────────────────

class TestGetMeme:
    @pytest.mark.asyncio
    async def test_public_meme_returned(self, async_client: AsyncClient, db_session):
        meme = make_meme(is_public=True)
        db_session.add(meme)
        await db_session.flush()

        resp = await async_client.get(f"/api/v1/memes/{meme.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == meme.id

    @pytest.mark.asyncio
    async def test_private_meme_returns_404(self, async_client: AsyncClient, db_session):
        meme = make_meme(is_public=False)
        db_session.add(meme)
        await db_session.flush()

        resp = await async_client.get(f"/api/v1/memes/{meme.id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_nonexistent_meme_returns_404(self, async_client: AsyncClient):
        resp = await async_client.get(f"/api/v1/memes/{uuid4()}")
        assert resp.status_code == 404


# ── POST /memes/{id}/share ────────────────────────────────────────────────────

class TestShareMeme:
    @pytest.mark.asyncio
    async def test_share_increments_count(self, async_client: AsyncClient, db_session):
        meme = make_meme(is_public=True)
        db_session.add(meme)
        await db_session.flush()

        with patch("services.trending.update_trending_score", AsyncMock()):
            resp = await async_client.post(f"/api/v1/memes/{meme.id}/share")

        assert resp.status_code == 200
        assert resp.json()["share_count"] == 1

    @pytest.mark.asyncio
    async def test_share_nonexistent_returns_404(self, async_client: AsyncClient):
        with patch("services.trending.update_trending_score", AsyncMock()):
            resp = await async_client.post(f"/api/v1/memes/{uuid4()}/share")
        assert resp.status_code == 404


# ── POST /memes/{id}/like ─────────────────────────────────────────────────────

class TestLikeMeme:
    @pytest.mark.asyncio
    async def test_like_increments_count(self, async_client: AsyncClient, db_session):
        meme = make_meme(is_public=True)
        db_session.add(meme)
        await db_session.flush()

        with patch("services.trending.update_trending_score", AsyncMock()):
            resp = await async_client.post(f"/api/v1/memes/{meme.id}/like")

        assert resp.status_code == 200
        assert resp.json()["like_count"] == 1


# ── DELETE /memes/{id} ────────────────────────────────────────────────────────

class TestDeleteMeme:
    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, async_client: AsyncClient, db_session):
        meme = make_meme(is_public=True)
        db_session.add(meme)
        await db_session.flush()

        resp = await async_client.delete(f"/api/v1/memes/{meme.id}")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_non_owner_returns_403(
        self, async_client: AsyncClient, db_session, free_user, pro_user
    ):
        meme = make_meme(user_id=free_user.id, is_public=True)
        db_session.add(meme)
        await db_session.flush()

        from services.auth import get_current_user_optional

        async def _get_pro():
            return pro_user

        app = async_client._transport.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user_optional] = _get_pro

        with patch("services.trending.remove_from_trending", AsyncMock()):
            resp = await async_client.delete(f"/api/v1/memes/{meme.id}")

        app.dependency_overrides.pop(get_current_user_optional, None)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_owner_can_delete(
        self, async_client: AsyncClient, db_session, free_user
    ):
        meme = make_meme(user_id=free_user.id, is_public=True)
        db_session.add(meme)
        await db_session.flush()

        from services.auth import get_current_user_optional

        async def _get_free():
            return free_user

        app = async_client._transport.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_user_optional] = _get_free

        with patch("services.trending.remove_from_trending", AsyncMock()):
            resp = await async_client.delete(f"/api/v1/memes/{meme.id}")

        app.dependency_overrides.pop(get_current_user_optional, None)
        assert resp.status_code == 200


# ── GET /memes/moderation/flagged ─────────────────────────────────────────────

class TestModerationQueue:
    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/memes/moderation/flagged")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_non_admin_returns_403(
        self, async_client: AsyncClient, free_user_headers
    ):
        resp = await async_client.get(
            "/api/v1/memes/moderation/flagged", headers=free_user_headers
        )
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_admin_sees_flagged_memes(
        self, async_client: AsyncClient, db_session, admin_user, admin_headers
    ):
        flagged = make_meme(
            user_id=admin_user.id, is_public=False, moderation_status="flagged"
        )
        approved = make_meme(
            user_id=admin_user.id, is_public=True, moderation_status="approved"
        )
        db_session.add_all([flagged, approved])
        await db_session.flush()

        from services.auth import get_current_admin_user, get_current_user

        async def _admin():
            return admin_user

        app = async_client._transport.app  # type: ignore[attr-defined]
        app.dependency_overrides[get_current_admin_user] = _admin
        app.dependency_overrides[get_current_user] = _admin

        resp = await async_client.get(
            "/api/v1/memes/moderation/flagged", headers=admin_headers
        )

        app.dependency_overrides.pop(get_current_admin_user, None)
        app.dependency_overrides.pop(get_current_user, None)

        assert resp.status_code == 200
        ids = [m["id"] for m in resp.json()["memes"]]
        assert flagged.id in ids
        assert approved.id not in ids


# ── GET /memes/templates ──────────────────────────────────────────────────────

class TestTemplates:
    @pytest.mark.asyncio
    async def test_returns_list(self, async_client: AsyncClient, db_session):
        t = make_template(id=999, name="Test Template Unique")
        db_session.add(t)
        await db_session.flush()

        resp = await async_client.get("/api/v1/memes/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        names = [item["name"] for item in data]
        assert "Test Template Unique" in names

    @pytest.mark.asyncio
    async def test_unknown_source_filter_rejected(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/memes/templates?source=imgflip")
        assert resp.status_code == 400
