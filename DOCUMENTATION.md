# 🧙 MemeGPT Documentation

Comprehensive guide for MemeGPT - an AI-powered meme generator.

---

## 📚 Table of Contents
1. [Introduction](#1-introduction)
2. [Architecture](#2-architecture)
3. [Getting Started](#3-getting-started)
4. [Configuration & Rate Limiting](#4-configuration--rate-limiting)
5. [Testing & Verification](#5-testing--verification)
6. [Maintenance & Monitoring](#6-maintenance--monitoring)
7. [Troubleshooting](#7-troubleshooting)
8. [Contributing & Support](#8-contributing--support)

---

## 1. Introduction
MemeGPT leverages OpenAI (GPT-4o) and Google Gemini models to create intelligent memes. It automatically selects templates, generates captions, and handles image synthesis.

### Key Features
- **Multi-Model AI**: Failover between OpenAI and Gemini for captions.
- **Imgflip Integration**: Access to 100+ popular templates with local fallback.
- **Manual Editor**: Precise control over text placement and styling.
- **Async Processing**: ARQ-powered job queue for non-blocking generation.
- **Optimized Storage**: Cloudflare R2 integration for CDN-ready delivery.
- **Subscription Support**: Stripe integration with tiered rate limiting.

---

## 2. Architecture

### Directory Structure
```
MemeGPT/
├── backend/            # FastAPI, ARQ Workers, SQLAlchemy
├── frontend/           # React + Vite + TypeScript
├── scripts/            # Deployment and maintenance scripts
└── docker-compose.yml  # Container orchestration
```

### Tech Stack
- **Backend**: Python (FastAPI), ARQ (Redis Queue), PostgreSQL (SQLAlchemy).
- **Frontend**: React, TypeScript, Vite.
- **Infrastructure**: Redis (Cache/Queue), Cloudflare R2 (Storage), Sentry (Monitoring).

---

## 3. Getting Started

### Prerequisites
- Python 3.10+, Node.js 18+, Docker, Git.
- API Keys: OpenAI, Gemini, Stripe (Optional), Cloudflare R2 (Optional).

### Quick Setup (Local)
1. **Backend**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Or venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env      # Configure your keys
   alembic upgrade head      # Run migrations
   uvicorn main:app --reload
   ```

2. **Worker**:
   ```bash
   cd backend
   python -m arq workers.meme_worker.WorkerSettings
   ```

3. **Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

### Docker Setup
```bash
docker-compose up -d
```

---

## 4. Configuration & Rate Limiting

### Environment Variables
Configure these in `backend/.env`. See `.env.example` for all options.
- `DATABASE_URL`: PostgreSQL connection string.
- `REDIS_URL`: Redis connection string.
- `AI_PROVIDER`: `openai`, `gemini`, or `both`.
- `RATE_LIMIT_ENABLED`: Set to `true` to enable limits.

### Rate Limit Tiers
Limits are enforced via a sliding window algorithm in Redis.
- **Free**: 10 req/hr (2 req/min burst).
- **Pro**: 500 req/hr (50 req/min burst).
- **API**: 1000 req/hr (100 req/min burst).

---

## 5. Testing & Verification

### Local Template Testing
1. **Direct Access**: Check `http://localhost:8000/frames/Drake-Hotline-Bling.jpg`.
2. **API Check**: Verify `GET /api/memes/templates` returns valid JSON.
3. **Seeding**: Use `POST /api/memes/seed-templates` to refresh template data.

### Automation
- **Backend**: `cd backend && pytest`
- **Frontend**: `cd frontend && npm test`

---

## 6. Maintenance & Monitoring

### Daily Tasks
- **Health Checks**: `curl http://localhost:8000/api/health`.
- **Log Review**: `docker-compose logs --since 24h | grep -i error`.

### Periodic Maintenance
- **Database**: Run `VACUUM ANALYZE` weekly; clean old `jobs` (>90 days) monthly.
- **Storage**: Clean temporary files (`/app/output`) weekly.
- **Backups**: Use `pg_dump` for DB and verify R2 backup integrity.

### Storage Maintenance
The `backend/public/` directory serves as fallback storage when Cloudflare R2 is unavailable.

- **Check Metrics**: `GET /api/storage/metrics`
- **Manual Cleanup**:
  ```bash
  # Delete files older than 7 days
  python scripts/cleanup_storage.py --cleanup-age --max-age-days 7
  # Reduce size to 500 MB
  python scripts/cleanup_storage.py --cleanup-size --max-size-mb 500
  ```
- **R2 Migration**: `python scripts/cleanup_storage.py --migrate-to-r2`
- **Automated Cleanup**: Add `0 2 * * * python scripts/cleanup_storage.py --scheduled` to crontab.

### Monitoring
Monitor CPU (<80%), Memory (<85%), and API response times (<500ms). Use Sentry for real-time error tracking.

---

## 7. Troubleshooting

### Common Issues
- **AI Formatting Failures**: Handled by field mapping in `meme_ai.py`.
- **Template 404s**: Ensure Imgflip credentials or local templates in `public/frames`.
- **Provider Outages**: System automatically fails over between OpenAI and Gemini.
- **Rate Limited**: Check `X-RateLimit-Remaining` headers and wait for `Retry-After`.

### Recovery
- **Database Restore**: `pg_restore -d memegpt < backup.sql`.
- **System Restore**: Stop services, restore DB/Storage, verify integrity, restart.

---

## 8. Contributing & Support
- **Bugs**: Open an issue on GitHub with reproduction steps.
- **Enhancements**: PRs welcome for UI/UX, AI prompts, or new templates.
- **Support**: support@memegpt.dev | [GitHub Issues](https://github.com/dhananjaylab/MemeGPT/issues)
