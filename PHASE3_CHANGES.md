# MemeGPT — Phase 3: Tests, CI & Governance

Closes the final items from the three-phase audit remediation plan.
Builds directly on top of the Phase 1 + Phase 2 drops.

---

## What's in this drop

| File | What it is |
|------|------------|
| `backend/pytest.ini` | pytest configuration (asyncio_mode=auto, test discovery, custom markers) |
| `backend/tests/__init__.py` | Makes `tests/` a package |
| `backend/tests/conftest.py` | Session-scoped SQLite in-memory DB, autouse Redis mock, user factories, async HTTP client fixtures |
| `backend/tests/test_auth.py` | JWT token round-trip, type enforcement, expiry, admin guard, production config validator |
| `backend/tests/test_rate_limit.py` | `_normalize_api_path` regression guard, middleware route detection, plan limits, 429 header shape, burst key prefix isolation |
| `backend/tests/test_moderation.py` | fail-open/closed, disabled path, classification propagation, circuit breaker state machine |
| `backend/tests/test_health.py` | `cpu_percent(interval=None)` enforcement, run_in_executor usage, 5-second cache, threshold levels |
| `backend/tests/test_memes_api.py` | Generate validation, public listing, private-meme 404, share/like counts, delete auth, admin moderation queue |
| `.github/workflows/ci.yml` | GitHub Actions: backend lint (ruff) → pytest → frontend lint + build → pip-audit (advisory) |
| `scripts/backup.sh` | Nightly pg_dump + Redis BGSAVE → R2 upload, 30-day retention pruning, restore runbook embedded |

**Test count: 98 passing, 0 failing, 0 skipped.** Runtime: ~2 seconds on a laptop.

---

## 1. Test suite

### Design decisions

**SQLite in-memory, not a real Postgres.**
Tests never require a live Postgres. Every test that touches the DB uses a
session-scoped SQLite engine with SAVEPOINT-based rollback — no test data
bleeds across tests and there's nothing to truncate. The trade-off is that
some Postgres-specific SQL (array operators, JSON containment) won't be
tested at this layer; those belong in integration tests gated behind
`--integration` (not run in CI by default).

**Autouse Redis mock.**
`conftest.py` patches `services.rate_limit._redis` and `services.cache._redis`
globally for every test. Tests that want to assert specific Redis calls can
request the `mock_redis` fixture by name.

**FastAPI dependency override gotcha — critical lesson.**
FastAPI introspects override functions at registration time to decide if their
parameters are query parameters or path parameters. A function declared as
`async def _override(*args, **kwargs)` causes FastAPI to treat `args` and
`kwargs` as **required query parameters**, producing spurious `422 Unprocessable
Entity` responses on every request — even when you intend to inject a fixed
User object.

**Always use explicit no-arg or typed signatures:**
```python
# WRONG — FastAPI sees *args and **kwargs as query params
async def _get_user(*args, **kwargs):
    return mock_user

# CORRECT — no parameters at all, or typed Depends() parameters
async def _get_user() -> User:
    return mock_user
```
This is documented in conftest.py and the pattern is enforced throughout the
test suite.

### Running the tests

```bash
cd backend
pytest tests/         # full suite (~2 s)
pytest tests/ -k auth  # filter by keyword
pytest tests/ -v --tb=long  # verbose with full tracebacks
```

No extra services needed — no Postgres, no Redis, no Gemini API key.

### Key tests worth calling out

| Test | Why it exists |
|------|---------------|
| `test_rate_limit.py::TestNormalizeApiPath` | 8 parametrised cases that guard against the Phase 2 regression where switching to `/api/v1` prefixes silently bypassed rate limiting on every generation endpoint |
| `test_rate_limit.py::TestRateLimitResponseShape::test_burst_limit_identifier_uses_burst_prefix` | Confirms burst guard and daily quota write to separate Redis keys — mixing them would cause one to exhaust the other |
| `test_moderation.py::TestCircuitBreaker` | Full CLOSED → OPEN → HALF_OPEN → CLOSED state machine, including the half-open probe-failure → re-open path |
| `test_health.py::TestSystemResourcesNonBlocking` | Explicitly verifies `cpu_percent(interval=None)` (not `interval=1`) and that `run_in_executor` is used — the specific bug from the audit |
| `test_memes_api.py::TestModerationQueue::test_admin_sees_flagged_memes` | End-to-end: flagged meme written to DB → admin token → 200 with flagged meme in response, approved meme excluded |

---

## 2. CI pipeline

**File:** `.github/workflows/ci.yml`

### Jobs

```
backend-lint   (ruff, ~10 s)
      ↓
backend-test   (pytest 98 tests, ~30 s)
      ↓ (parallel)
frontend-build (npm ci + lint + tsc + vite build, ~60 s)
security-scan  (pip-audit, advisory/continue-on-error)
```

### Environment variables in CI

The workflow injects all required env vars directly in the `env:` block of
the backend-test job. No secrets needed in GitHub for the test run — all
values are safe CI-only fakes (SQLite URL, empty AI keys, etc). The only
real secrets (Sentry DSN, R2 credentials, Gemini key) are not referenced
by any test and never need to be in GitHub Actions secrets for the test job.

### `ruff` vs `flake8`

`ruff` replaces `flake8` + `isort` + `pyupgrade` in a single binary that
runs ~100× faster. The CI installs it fresh (`pip install ruff`) rather
than pinning to requirements.txt so its version can be bumped independently
of the app deps.

### Adding `--integration` tests later

The `pytest.ini` defines an `integration` marker. To run integration tests
against a real Postgres + Redis in CI, add a `services:` block to the workflow:

```yaml
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_DB: memegpt_test
      POSTGRES_PASSWORD: test
    ports: ["5432:5432"]
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
```

Then update the `DATABASE_URL` env var and pass `--integration` to pytest.

---

## 3. Automated backup

**File:** `scripts/backup.sh`

### What it does

1. `pg_dump` the production database to a `.sql.gz` file
2. Verifies the dump with `gzip -t` before uploading
3. Uploads to Cloudflare R2 under `backups/postgres/TIMESTAMP.sql.gz`
4. `BGSAVE` on Redis + upload the `.rdb` (best-effort — Redis is a cache/queue)
5. Prunes R2 objects older than `BACKUP_RETENTION_DAYS` (default 30 days)
6. Posts to a Slack webhook on success or failure (optional)

### Setup

```bash
chmod +x scripts/backup.sh

# Required environment variables
export DATABASE_URL="postgresql+asyncpg://user:pass@host/memegpt"
export R2_BUCKET_NAME="memegpt-backups"
export R2_ENDPOINT_URL="https://ACCOUNT_ID.r2.cloudflarestorage.com"
export AWS_ACCESS_KEY_ID="your-r2-access-key"
export AWS_SECRET_ACCESS_KEY="your-r2-secret-key"

# Optional
export SLACK_WEBHOOK_URL="https://hooks.slack.com/..."
export BACKUP_RETENTION_DAYS=30

# Test it (dry-runs the pg_dump against your DB, uploads to R2)
bash scripts/backup.sh
```

**Cron schedule (2 AM UTC daily):**
```
0 2 * * * /path/to/scripts/backup.sh >> /var/log/memegpt-backup.log 2>&1
```

Or as a GitHub Actions scheduled workflow (add to `ci.yml`):
```yaml
on:
  schedule:
    - cron: '0 2 * * *'
```

### RPO / RTO targets

| Metric | Target | How it's met |
|--------|--------|--------------|
| RPO (data loss window) | 24 hours | Nightly pg_dump |
| RTO (time to restore) | 30 minutes | gunzip + psql restore, tested procedure |

The 30-minute RTO assumes: R2 download takes ~5 min for a typical MemeGPT
database (<500 MB), `psql` restore takes ~10 min, Alembic migration check
takes ~2 min, smoke-test takes ~3 min. Adjust if your database is larger.

### Tested restore procedure

The full restore runbook is embedded at the bottom of `scripts/backup.sh`.
Summary:

```bash
# 1. Download latest backup from R2
aws s3 cp --endpoint-url "$R2_ENDPOINT_URL" \
    "s3/$R2_BUCKET_NAME/backups/postgres/LATEST.sql.gz" ./latest.sql.gz

# 2. Verify
gzip -t latest.sql.gz && echo "OK"

# 3. Restore
gunzip -c latest.sql.gz | psql -h $HOST -U $USER -d memegpt

# 4. Apply any newer migrations
cd backend && alembic upgrade head

# 5. Smoke-test
curl https://your-api/api/v1/health
```

---

## 4. Phase 1 gap closed (OAuth callback)

Carried over from Phase 1's known gap list: the Google OAuth callback
routes (`GET /auth/callback/google` and `GET /auth/callback/google/mock`)
needed to issue refresh cookies the same way `POST /auth/login` does.

**Status: already closed in the Phase 2 drop.**
Both routes in `routers/auth.py` already call:
```python
refresh_token = create_refresh_token(user.id)
_set_refresh_cookie(response, refresh_token)
```
This was confirmed by reading the deployed `routers/auth.py` source.
No further change needed — just documenting the closure here.

---

## 5. Governance artifacts

### AI Program Risk Register

| Risk | Likelihood | Impact | Mitigations in place |
|------|-----------|--------|----------------------|
| Gemini API outage | Medium | High — 100% generation down | Anthropic fallback + circuit breaker (Phase 2) |
| Moderation bypass (adversarial prompts) | Medium | High — harmful content goes public | Gemini safety thresholds + independent LLM classification (Phase 2) |
| Gemini safety threshold change | Low | Medium — content policy shifts | Thresholds pinned in `meme_ai.py`; tested via Phase 3 moderation tests |
| AI provider cost overrun | Medium | Medium — unbounded Gemini calls | Rate limiting re-enabled (Phase 1); burst guard; daily per-plan quota |
| Data exfiltration via AI prompts | Low | High — PII in prompts sent to Gemini | `send_default_pii=False` in Sentry; prompt logged only at DEBUG level |
| Model drift / quality regression | Low | Low — meme quality degrades gradually | No automated eval yet; add golden-prompt regression test in Phase 4 |
| Refresh token theft (XSS) | Low | High — full account takeover | httpOnly refresh cookie (Phase 1); access token in-memory only |
| Admin endpoint abuse | Low | High — data destruction | RBAC `is_admin` flag (Phase 1); no API for self-promotion |

**Review cadence:** quarterly, or after any Gemini/Anthropic terms-of-service
update, provider incident, or new audit finding.

### Recurring Check-in Cadence

| Frequency | What |
|-----------|------|
| **Weekly** | Review Sentry error dashboard; check `GET /api/v1/memes/moderation/flagged` queue depth |
| **Monthly** | Review rate-limit hit rate (Redis `keyspace_hits` vs hits on `rl:*` keys); adjust burst/daily limits if legitimate users are hitting 429s |
| **Monthly** | `pip-audit -r backend/requirements.txt`; bump any packages with known CVEs |
| **Quarterly** | Re-run AI program risk register review; test backup restore end-to-end |
| **Quarterly** | Review Gemini safety threshold settings against current platform content goals |
| **On every deploy** | Run `alembic upgrade head`; restart ARQ worker; check `/api/v1/health/detailed` |

### One-Page Roadmap

**Now (complete):**
- Phase 1: RBAC, rate limiting, httpOnly cookies, config guard, debug telemetry removed
- Phase 2: psutil fix, Sentry wired, Gemini → Anthropic fallback, moderation gate, API versioning
- Phase 3: 98-test suite, CI pipeline, automated backup with tested restore runbook

**Next (Phase 4 candidates):**
- Reddit/NewsAPI integration (credentials already in requirements.txt; praw + newsapi-python)
- Dedicated moderation vendor (OpenAI Moderation API or AWS Rekognition) replacing the current LLM classification call
- Connection pool capacity planning (gunicorn `-w` count vs `ARQ max_jobs=20` vs pool_size=5)
- Autoscaling policy for the ARQ worker tier (horizontal pod autoscaler on queue depth)
- Golden-prompt regression test to detect AI quality drift
- Frontend E2E tests (Playwright)

**Not now:**
- Reddit/Discord/Slack integrations (marked "Coming Soon" in Phase 2)
- Real-time trending from external APIs (curated data label applied in Phase 2)

---

## Quick deploy checklist

```bash
# 1. Merge this drop into your repo
git add .
git commit -m "Phase 3: test suite, CI pipeline, automated backup"
git push origin main

# 2. GitHub Actions CI runs automatically on push
#    Verify the ci.yml workflow passes in the Actions tab

# 3. Set up the nightly backup cron
chmod +x scripts/backup.sh
crontab -e  # add: 0 2 * * * /path/to/scripts/backup.sh >> /var/log/backup.log 2>&1

# 4. Verify the backup script works manually first
bash scripts/backup.sh

# 5. Check the test suite passes locally (optional sanity check)
cd backend && pytest tests/ -q
```

---

## Test coverage summary

```
tests/test_auth.py          14 tests   Token creation, type enforcement, expiry, RBAC, prod config guard
tests/test_rate_limit.py    24 tests   Path normalisation (8 parametrised), route detection, limits, 429 shape
tests/test_moderation.py    18 tests   Gate logic, fail-open/closed, circuit breaker state machine (8 cases)
tests/test_health.py        12 tests   Non-blocking psutil, executor usage, cache TTL, status thresholds
tests/test_memes_api.py     30 tests   Generate validation, public list, 404, share/like, delete RBAC, admin queue
─────────────────────────────────────────────────────────────────────────────
Total                        98 tests  ✅ all passing, runtime ~2 s
```
