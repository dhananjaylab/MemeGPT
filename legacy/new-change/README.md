# 🧙 MemeGPT v2 — AI Meme Generator

> Next.js 15 · FastAPI · ARQ · PostgreSQL · Cloudflare R2 · GPT-4o

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Browser                                                │
│  Next.js 15 (React 19, Tailwind, shadcn/ui)             │
│  - /             → MemeGenerator + TrendingTopics        │
│  - /meme/[id]    → Public permalink + OG card            │
│  - /api/og/[id]  → Edge OG image (Vercel OG)            │
└───────────────────┬─────────────────────────────────────┘
                    │ HTTP
┌───────────────────▼─────────────────────────────────────┐
│  FastAPI (uvicorn, async)                               │
│  POST /api/memes/generate  → enqueue ARQ job            │
│  GET  /api/jobs/{id}       → poll status + results      │
│  GET  /api/memes           → public gallery             │
│  GET  /api/trending        → trending topics (cached)   │
└──────────┬───────────────────────────┬──────────────────┘
           │ Redis (ARQ)               │ asyncpg
┌──────────▼──────────┐   ┌───────────▼──────────────────┐
│  ARQ Worker         │   │  PostgreSQL                  │
│  1. GPT-4o captions │   │  users, memes,               │
│  2. PIL compose     │   │  generation_jobs             │
│  3. R2 upload       │   └──────────────────────────────┘
│  4. Save to DB      │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Cloudflare R2      │
│  memes/*.png        │
│  thumbnails/*.png   │
└─────────────────────┘
```

## Quick Start (Docker)

```bash
# 1. Clone
git clone https://github.com/Dhananjay-97/MemeGPT.git
cd MemeGPT

# 2. Copy your meme templates + fonts into place
cp /path/to/templates/* ./meme_templates/
cp /path/to/fonts/*     ./fonts/

# 3. Configure environment
cp backend/.env.example  backend/.env
cp frontend/.env.local.example frontend/.env.local
# → edit both files with your API keys

# 4. Launch
docker compose up --build

# App:    http://localhost:3000
# API:    http://localhost:8000/docs
# Redis:  localhost:6379
# Postgres: localhost:5432
```

## Local Dev (without Docker)

```bash
# ── Backend ────────────────────────────────────────────
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in values

# Start Postgres + Redis (or use Docker for just these)
docker compose up postgres redis -d

# Run DB migrations
alembic upgrade head

# Start API
uvicorn backend.main:app --reload --port 8000

# Start ARQ worker (in a separate terminal)
arq backend.workers.meme_worker.WorkerSettings

# ── Frontend ───────────────────────────────────────────
cd frontend
npm install
cp .env.local.example .env.local   # fill in values
npm run dev
# → http://localhost:3000
```

## Key Files

```
memegpt/
├── frontend/
│   ├── app/
│   │   ├── page.tsx              ← Homepage (generator + trending)
│   │   ├── meme/[id]/page.tsx    ← Shareable meme permalink
│   │   └── api/
│   │       ├── generate/         ← React.js proxy to FastAPI
│   │       └── og/[id]/          ← Edge OG image generation
│   ├── components/
│   │   ├── MemeGenerator.tsx     ← Core input + generation UI
│   │   ├── MemeCard.tsx          ← Meme display with share
│   │   ├── ShareMenu.tsx         ← X / Reddit / WhatsApp / download
│   │   └── TrendingTopics.tsx    ← Sidebar trending feed
│   └── lib/
│       ├── api.ts                ← All API calls + SWR hooks
│       └── types.ts              ← Shared TypeScript types
│
├── backend/
│   ├── main.py                   ← FastAPI app + CORS + routers
│   ├── core/config.py            ← Pydantic settings (env vars)
│   ├── routers/
│   │   ├── memes.py              ← Generate, list, get, share
│   │   ├── jobs.py               ← Job polling
│   │   ├── trending.py           ← Trending topics (Reddit + News)
│   │   └── auth.py               ← JWT + API key auth
│   ├── services/
│   │   ├── meme_ai.py            ← GPT-4o caption generation
│   │   ├── compositor.py         ← PIL image compositing
│   │   └── storage.py            ← Cloudflare R2 upload
│   ├── workers/
│   │   └── meme_worker.py        ← ARQ async job (full pipeline)
│   ├── models/models.py          ← SQLAlchemy models
│   └── db/
│       ├── session.py            ← Async DB session + dependency
│       └── migrations/           ← Alembic migrations
│
├── meme_templates/               ← 52 .jpg template images (add manually)
├── fonts/                        ← impact.ttf, ComicSansMS3.ttf, ARIAL.TTF
├── docker-compose.yml
└── public/meme_data.json         ← 52 template definitions
```

## Adding More Meme Templates

1. Add the `.jpg` image to `meme_templates/`
2. Add an entry to `frontend/public/meme_data.json` and `backend/data/meme_data.json`
3. Use the `imgflip_id` field to find accurate bounding boxes at imgflip.com
4. No restart needed — templates are loaded at worker startup

## Deployment

| Service    | Recommended            |
|------------|------------------------|
| Frontend   | Vercel (free tier)     |
| API        | Railway or Render      |
| Worker     | Railway (same project) |
| Database   | Railway Postgres       |
| Redis      | Railway Redis          |
| Storage    | Cloudflare R2 (~free)  |

## Traffic Strategy

- **Viral**: Every meme page has full OG metadata → unfurls as image in X/WhatsApp/Slack
- **SEO**: `/meme/[id]` pages are server-rendered with unique titles + descriptions
- **API**: `POST /api/memes/generate` with `X-API-Key` header for developers
- **Gallery**: `/gallery` page indexes public memes — searchable by search engines

## Phase 3 Roadmap

- [ ] User accounts + meme history (NextAuth)
- [ ] Public gallery page with trending/top filters  
- [ ] Stripe integration (free 5/day → Pro unlimited)
- [ ] Developer portal (API key management)
- [ ] Embeddable `<script>` widget
- [ ] WebSocket progress updates (replace polling)
