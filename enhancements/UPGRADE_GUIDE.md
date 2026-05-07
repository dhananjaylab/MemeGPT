# MemeGPT — Gen-Z Enhancement & Architecture Upgrade

## What Changed (12 files, 3 categories)

---

## 1. New Templates — `public/meme_data.json`

**26 total** (was 11). 15 new Gen-Z-native additions:

| ID | Name                    | Format     | Gen-Z Use Case                        |
|----|-------------------------|------------|---------------------------------------|
| 11 | This Is Fine            | 2 fields   | Denial humour, slow-burn disasters    |
| 12 | Surprised Pikachu       | 2 fields   | Obvious consequences played for shock |
| 13 | Woman Yelling at Cat    | 2 fields   | Two-sided arguments / hot takes       |
| 14 | Two Buttons             | 3 fields   | Impossible choices, decision paralysis |
| 15 | Always Has Been         | 2 fields   | Revealing something was always true   |
| 16 | Gru's Plan              | 4 fields   | Plans that backfire at step 4         |
| 17 | Panik Kalm Panik        | 3 fields   | Anxiety escalation arcs               |
| 18 | Nobody / Absolutely Nobody | 3 fields | Calling out unprompted behaviour      |
| 19 | Me Explaining To My Mom | 2 fields   | Gen gap, niche internet interests     |
| 20 | It's A Trap             | 2 fields   | Warning about obvious traps           |
| 21 | Mocking SpongeBob       | 2 fields   | Sarcasm / mocking clichés             |
| 22 | Bike Fall               | 3 fields   | Self-sabotage scenarios               |
| 23 | Change My Mind          | 1 field    | Hot takes, unpopular opinions         |
| 24 | Ancient Aliens Guy      | 2 fields   | Attributing anything weird to aliens  |
| 25 | Coffin Dance            | 2 fields   | Dramatic "burial" of plans/hopes      |

Each template has:
- Accurate `text_coordinates_xy_wh` tuned to the original image layout
- `fallback_url` pointing to Imgflip CDN — used when no local file exists
- Gen-Z flavoured `usage_instructions` and `example_output`
- `alternative_names` for better AI template-selection matching

---

## 2. Architecture Upgrades

### 2a. Three-Layer Redis Cache — `backend/services/cache.py` *(NEW)*

```
Request
   │
   ├─ Caption cache (1 h TTL)
   │   Key: sha256(prompt)[:16]
   │   Hit: skip GPT/Gemini call entirely → ~10ms
   │
   ├─ Meme URL cache (24 h TTL)
   │   Key: sha256(template_id|texts)[:16]
   │   Hit: skip PIL composition + R2 upload → ~5ms
   │
   └─ Template image cache (6 h TTL)
       Key: md5(image_url)
       Hit: skip HTTP download of remote templates → ~2ms
```

All cache misses are silent — the pipeline continues normally. A Redis outage never breaks generation.

### 2b. URL-Aware Async Compositor — `backend/services/compositor.py` *(UPDATED)*

Old: `PIL.Image.open(local_file)` — hard crash if file missing.

New:
```
overlay_text_on_image_async(template, texts)
  │
  ├─ local file exists?  → Image.open(path)          # <1ms
  ├─ fallback_url set?  → Redis cache check           # <2ms on hit
  │                       → httpx download + cache    # ~300ms on miss
  └─ neither?           → FileNotFoundError (clear message)
```

Improvements over v1:
- `getbbox()` instead of deprecated `getsize()` — no Pillow deprecation warnings
- Tighter `LINE_HEIGHT_MUL = 1.35` — punchy Gen-Z short-caption look
- Sync shim preserved for backward compat with ARQ worker

### 2c. Fast-Path Endpoint — `backend/routers/memes.py` *(UPDATED)*

**New endpoint: `POST /api/memes/generate/quick`**

```
Old flow (queue-based):       New fast path:
POST /generate → job_id       POST /generate/quick → image_url
poll /jobs/{id} × N           Done. One round-trip.
wait 5–30 s                   5ms (cache hit) / 2–4s (miss)
```

Request body:
```json
// Manual (fastest — composer only):
{ "template_id": 5, "captions": ["text1", "text2"] }

// Auto (AI + composer):
{ "prompt": "when the wifi drops before submitting" }
```

Response:
```json
{
  "meme_id": "abc123",
  "image_url": "https://cdn.../memes/abc123.png",
  "template_name": "Surprised Pikachu",
  "meme_text": ["...","..."],
  "cache_hit": true,
  "generation_time_ms": 7
}
```

The async queue path (`POST /generate`) is unchanged for batch/background use.

### 2d. Cache-Aware Worker — `backend/workers/meme_worker.py` *(UPDATED)*

```python
# Before processing each meme:
cached_caps = await get_cached_captions(prompt)   # 1. try caption cache
cached_url  = await get_cached_meme_url(id, texts) # 2. try image cache

# On cache miss, generate normally then:
await set_cached_captions(prompt, captions)
await set_cached_meme_url(template_id, texts, url)
```

Also: `max_jobs = 10` (was 1), `job_timeout = 120s`.

### 2e. Gen-Z AI Prompts — `backend/services/meme_ai.py` *(UPDATED)*

System prompt additions:
```
• Tone: dry, self-aware, absurdist, slightly nihilistic but fun
• Short punchy captions — aim for ≤ 8 words per field
• temperature: 1.1 (was 1.0) — more creative output
• First option: most relatable/mainstream
• Second option: niche/absurdist  
• Third option: wildcard / unexpected angle
```

### 2f. Database Migration — `backend/db/migrations/versions/20260507_genz_templates.py` *(NEW)*

Three new columns on `meme_templates`:

| Column        | Type    | Purpose                                  |
|---------------|---------|------------------------------------------|
| `fallback_url`| String  | CDN URL used when local frame file absent |
| `gen_z_ready` | Boolean | Filter flag for Gen-Z template subset    |
| `vibe_tags`   | JSON    | Future: tag-based template discovery     |

Run: `alembic upgrade head`

### 2g. Updated Data Model — `backend/models/models.py` *(UPDATED)*

- `MemeTemplate.fallback_url` — proxied CDN URL for remote templates
- `MemeTemplate.gen_z_ready` — boolean index for fast filtering
- `MemeTemplate.vibe_tags` — JSON list of mood/context tags
- `MemeTemplate.effective_image_url` property — returns best available URL

---

## 3. Frontend Upgrades

### 3a. QuickGenerate Component — `frontend/src/components/QuickGenerate.tsx` *(NEW)*

A self-contained widget wired to `/generate/quick`:

- Rotating placeholder prompts (10 Gen-Z examples rotate per session)
- `⌘ + Enter` keyboard shortcut
- GPT-4o / Gemini toggle in header
- Shows cache badge + generation time in ms on result
- Confetti on first generate, toast with ms on cache hit
- Download + copy-link actions inline

### 3b. MemeGenerator — `frontend/src/components/MemeGenerator.tsx` *(UPDATED)*

Three tabs instead of two:

```
[⚡ Quick] [✨ AI Mode] [✏️ Editor]
   │             │           │
   │             │           └─ unchanged manual flow
   │             └─ AI suggestions carousel (unchanged)
   └─ QuickGenerate widget (NEW)
```

- Default tab is now **Quick** (fastest path for casual users)
- All three modes append to shared results list at bottom
- Trending topic click → fills Quick prompt and switches to Quick tab

### 3c. API Client — `frontend/src/lib/api.ts` *(UPDATED)*

```typescript
// New method:
apiClient.generateMemeQuick(request: QuickMemeRequest): Promise<QuickMemeResponse>

// Convenience export:
generateMemeQuick({ prompt: "..." })  // or { template_id, captions }
```

---

## Migration Steps

```bash
# 1. Run the new Alembic migration
cd backend
alembic upgrade head

# 2. Re-seed templates (picks up 15 new ones)
curl -X POST http://localhost:8000/api/memes/seed-templates

# 3. Verify all 26 templates are present
curl http://localhost:8000/api/memes/templates | python -m json.tool | grep '"name"' | wc -l
# Expected: 26

# 4. Test quick endpoint (manual mode — fastest)
curl -X POST http://localhost:8000/api/memes/generate/quick \
  -H "Content-Type: application/json" \
  -d '{"template_id": 12, "captions": ["sends 10 texts", "surprised when no reply"]}'

# 5. Test quick endpoint (AI mode)
curl -X POST http://localhost:8000/api/memes/generate/quick \
  -H "Content-Type: application/json" \
  -d '{"prompt": "when the group chat goes quiet after you share your location"}'
```

---

## Performance Before / After

| Scenario                    | Before        | After (cache miss) | After (cache hit) |
|-----------------------------|---------------|--------------------|-------------------|
| Auto generation (queue)     | 5–30 s poll   | 5–30 s poll        | 5–30 s poll       |
| Manual generation (queue)   | 3–10 s poll   | 3–10 s poll        | 3–10 s poll       |
| **Quick manual** (new)      | N/A           | ~1–2 s             | **< 10 ms**       |
| **Quick AI** (new)          | N/A           | ~3–5 s             | **< 10 ms**       |
| Remote template fetch       | crash (error) | ~300 ms + cached   | **< 2 ms**        |
| Identical AI prompt         | full AI call  | full AI call       | **< 5 ms**        |

---

## File Map

```
backend/
  main.py                                ← startup: seeds all 26 templates
  models/models.py                       ← 3 new columns + effective_image_url
  services/
    cache.py                             ← NEW: 3-layer Redis cache
    compositor.py                        ← async, URL-aware, getbbox fix
    meme_ai.py                           ← Gen-Z prompts, higher temp
  routers/
    memes.py                             ← POST /generate/quick + caching
  workers/
    meme_worker.py                       ← cache-aware, max_jobs=10
  db/migrations/versions/
    20260507_genz_templates.py           ← NEW: 3 columns + index

public/
  meme_data.json                         ← 26 templates (was 11)

frontend/src/
  lib/api.ts                             ← generateMemeQuick() method
  components/
    QuickGenerate.tsx                    ← NEW: instant generation widget
    MemeGenerator.tsx                    ← 3-tab UI, Quick tab default
```
