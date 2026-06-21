# MemeGPT — Phase 1 Implementation: Security & Cost Containment

This implements every item from Phase 1 of the remediation plan. 16 files
changed/added, listed below with exactly what changed and why. Drop these
into the matching paths in your repo (they preserve the original directory
structure — `backend/...`, `frontend/...`).

---

## 1. RBAC on destructive admin endpoints

**New:** `backend/models/models.py` — added `User.is_admin` (boolean, default `False`).
**New:** `backend/db/migrations/versions/20260620_add_is_admin.py` — Alembic migration for the column.
**New:** `backend/grant_admin.py` — CLI to grant/revoke admin, since there's deliberately no API endpoint that can self-promote a user (that would just relocate the hole).
**Changed:** `backend/services/auth.py` — added `get_current_admin_user` dependency (401 if unauthenticated, 403 if not admin).
**Changed:** `backend/routers/storage.py` — every endpoint (`/metrics`, `/cleanup/age`, `/cleanup/size`, `/migrate-to-r2`, `/cleanup/scheduled`) now requires `get_current_admin_user`. Previously these accepted an `Optional[User]` and never checked it — fully open to the internet.
**Changed:** `backend/routers/jobs.py` — `/queue/cleanup` now requires admin. `/queue/stats` (read-only counts) left public.
**Changed:** `backend/routers/memes.py` — `/seed-templates` now requires admin.

**Deploy steps:**
```bash
cd backend
alembic upgrade head
python grant_admin.py you@yourcompany.com   # bootstrap your own admin account
```

---

## 2. Generation rate limiting re-enabled + burst guard

**Changed:** `backend/core/middleware.py` — uncommented and re-enabled the block that rate-limits `POST /api/memes/generate*` (it was explicitly `# DISABLED FOR NOW`).
**Changed:** `backend/services/rate_limit.py` — added `check_generation_burst_limit()`, a short-window (default 5 req/60s) guard layered on top of the existing daily quota, specifically for generation endpoints, using a separate Redis key prefix (`rl:burst:`) so it doesn't interfere with the daily counter.
**Changed:** `backend/core/config.py` — added `generation_burst_limit` / `generation_burst_window_seconds` settings (env-overridable).

No migration needed — this is pure Redis-backed logic, same pattern as the existing daily quota.

**Tuning:** if `5 requests / 60s` is too tight for legitimate "AI Mode" users who fetch 3 suggestions then regenerate, raise `GENERATION_BURST_LIMIT` via env var rather than editing code.

---

## 3. Fail-fast production config validation

**Changed:** `backend/core/config.py` — added a `model_validator(mode="after")` that raises at `Settings()` construction (i.e., at process boot) if `ENVIRONMENT=production` and either:
- `SECRET_KEY` is still the placeholder default or under 32 characters, or
- `DATABASE_URL` still contains the `user:password@localhost` placeholder marker.

This means a misconfigured production deploy now **fails to start** with a clear error instead of silently serving traffic with a guessable JWT secret.

**Action required before your next production deploy:** generate a real secret —
```bash
openssl rand -hex 32
```
— and set it as `JWT_SECRET_KEY` (mapped to `secret_key` via the existing env loading). Same for `DATABASE_URL` pointing at your real database.

---

## 4. Debug telemetry removed from the production bundle

**Changed:** `frontend/src/components/TrendingTopics.tsx` — removed the three `fetch('http://127.0.0.1:7248/ingest/...')` debug calls that fired on every mount and every 5-minute refresh, shipping internal session/hypothesis IDs into the client bundle.
**Changed:** `frontend/vite.config.ts` — removed the matching debug block from the proxy-target resolution.

No env/config changes needed; this is a pure deletion. Functionally identical otherwise — diff the file if you want to confirm nothing else moved.

---

## 5. JWT moved off localStorage

This was the largest change. New flow:

- **Access token**: short-lived (default 60 min, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`), held **only in memory** on the frontend (a module-level variable in `lib/api.ts`, set by `AuthContext`). Never written to `localStorage` or `sessionStorage`.
- **Refresh token**: long-lived (default 7 days, `JWT_REFRESH_TOKEN_EXPIRE_DAYS`), issued as an **httpOnly, Secure (in prod), SameSite=Lax cookie** scoped to `/api/auth`. JavaScript can never read it — this is what actually closes the XSS-token-theft exposure, not just a shorter TTL.
- Refresh tokens **rotate** on every use (`POST /api/auth/refresh` issues both a new access token and a new refresh cookie).

**Changed:** `backend/services/auth.py` — `create_refresh_token`, `verify_refresh_token`, `REFRESH_COOKIE_NAME`; `create_access_token` now defaults to the short, settings-driven TTL instead of a hardcoded 7 days.
**Changed:** `backend/routers/auth.py` — `/login` now also sets the httpOnly refresh cookie; added `POST /refresh` and `POST /logout`.
**Changed:** `frontend/src/lib/api.ts` — added `setAccessToken`/`getAccessToken` (in-memory store), `credentials: 'include'` on every request (needed so the refresh cookie round-trips), `refreshAccessToken()`, `logout()`.
**Changed:** `frontend/src/context/AuthContext.tsx` — on mount, silently calls `refreshAccessToken()` instead of reading `localStorage`; `login()` stores the token in memory only; `logout()` calls the new backend endpoint to clear the cookie.

**⚠️ One known gap, by necessity:** the Google OAuth redirect flow (`Header.tsx` → `${VITE_API_URL}/auth/login/google` → backend → redirects to `/auth/callback?token=...`) is handled by a backend route that **wasn't included in the provided file set**, so I couldn't update it. Right now it will keep working exactly as before (issuing a token, landing on `AuthCallback.tsx`, which calls the unchanged `login()` signature) — but it won't get a refresh cookie, so OAuth-only users will be logged out after the access token's TTL (default 60 min) instead of being silently refreshed. **To close this gap:** update that OAuth callback route to call `create_refresh_token()` + set the same `refresh_token` httpOnly cookie (mirror `_set_refresh_cookie` in `routers/auth.py`) before redirecting to the frontend. This is not a new security hole — it's a UX regression (more frequent re-login) until that route is updated, and a good first task for Phase 2.

**Deploy steps:** no migration needed for this part. Just deploy backend + frontend together (the API contract for `/login` is backward-compatible — same request/response shape, it just *also* sets a cookie now).

---

## What's intentionally *not* in this drop

Per the 3-phase plan, Phase 1 is scoped to stop active bleeding. Still pending for Phase 2/3 (already detailed in the audit doc):
- Fixing the blocking `psutil.cpu_percent(interval=1)` call in the health check
- Wiring up Sentry/structlog (currently dependencies-only)
- AI provider fallback (Gemini → Anthropic) + content moderation before `is_public=True`
- Test suite / CI, backup automation, API versioning

---

## Quick verification checklist after deploying

- [ ] `alembic upgrade head` ran clean, `users.is_admin` column exists
- [ ] `python grant_admin.py <your email>` succeeded
- [ ] `curl -X POST .../api/storage/cleanup/age` with no auth header → `401`
- [ ] Same call with a non-admin user's bearer token → `403`
- [ ] Same call with your admin token → `200`
- [ ] Firing 6 rapid `POST /api/memes/generate/quick` calls in under a minute → the 6th returns `429`
- [ ] Production boot with placeholder `SECRET_KEY` → process refuses to start with a clear error
- [ ] Login in the browser → DevTools → Application → Cookies shows an httpOnly `refresh_token` cookie; **localStorage has no auth token**
- [ ] Refresh the page while logged in → still logged in (silent `/auth/refresh` call in the Network tab)
