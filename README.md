# 🧙 MemeGPT - Your Personal Meme Generator

Generate hilarious memes with ease using MemeGPT! This application leverages the power of AI to intelligently select meme templates and generate relevant captions.

---

## 🚀 Quick Links
- **[Frontend UI](http://localhost:5173)** - Local development UI.
- **[Backend API Docs](http://localhost:8000/docs)** - Interactive OpenAPI / Swagger documentation.
- **[GitHub Issues](https://github.com/dhananjaylab/MemeGPT/issues)** - Bug tracking and feature requests.

---

## 📚 Table of Contents
1. [Introduction & Features](#1-introduction--features)
2. [Architecture & Tech Stack](#2-architecture--tech-stack)
3. [Getting Started](#3-getting-started)
   - [Prerequisites](#prerequisites)
   - [Quick Setup (Local)](#quick-setup-local)
   - [Docker Setup](#docker-setup)
4. [Configuration & Rate Limiting](#4-configuration--rate-limiting)
5. [Testing & Verification](#5-testing--verification)
6. [Maintenance & Monitoring](#6-maintenance--monitoring)
   - [Daily Tasks](#daily-tasks)
   - [Periodic Maintenance](#periodic-maintenance)
   - [Storage Maintenance](#storage-maintenance)
   - [Monitoring](#monitoring)
7. [Troubleshooting](#7-troubleshooting)
8. [Contributing & Support](#8-contributing--support)
9. [License](#9-license)

---

## 1. Introduction & Features

MemeGPT leverages OpenAI (GPT-4o) and Google Gemini models to create intelligent memes. It automatically selects templates, generates captions, and handles image synthesis.

### ✨ Key Features
- **Multi-Model AI**: Failover between OpenAI (GPT-4o) and Google Gemini for robust caption generation.
- **Imgflip Integration**: Access to 100+ popular templates with local fallback capabilities.
- **Manual Editor**: Precise, full control over text placement, styling, and formatting.
- **Event-Driven Architecture**: Fast synchronous caching (<10ms) combined with ARQ background worker offloading and real-time Server-Sent Events (SSE) streaming for heavy generation tasks.
- **Secure API Key Management**: Strict "Store-Hash, Show-Once" lifecycle policy using SHA-256 hashing for API keys and masked prefix display.
- **Optimized Storage**: Cloudflare R2 integration for CDN-ready delivery with local filesystem fallback.
- **Subscription Support**: Stripe integration with tiered rate limiting.
- **Cloud Native**: Fully containerized with Docker and Docker Compose support.

---

## 2. Architecture & Tech Stack

### 🔒 API Key Lifecycle Policy ("Store-Hash, Show-Once")
To protect developer credentials and prevent unauthorized database access, MemeGPT enforces an enterprise-grade API key security policy:
- **Storage**: Plaintext API keys are **never** persisted in the database. All keys are hashed using `SHA-256` upon generation or migration.
- **Display**: The UI and database retain only a masked prefix (e.g., `mgpt_••••••••••`) for identification.
- **Generation & Rotation**: When a user generates or regenerates an API key, the plaintext key is displayed exactly **once** in the UI. If a key is lost, it cannot be retrieved and must be regenerated.

### ⚡ Quick Generation Flow (`/generate/quick`)
The `/generate/quick` endpoint employs a hybrid synchronous/asynchronous architecture to ensure high throughput and prevent worker thread exhaustion:
1. **Cache-First**: Requests are checked against Redis and database caches. On a hit, the final meme URL is returned instantly (<10ms).
2. **Worker Offload**: On a cache miss, heavy tasks (LLM requests, PIL rendering, R2 uploads) are offloaded to an ARQ background worker.
3. **Event-Driven Push**: The API immediately returns `202 Accepted` with a `job_id`. The client connects to the `/api/jobs/{job_id}/stream` Server-Sent Events (SSE) endpoint to receive real-time status updates and the final meme URL once processing completes.

### 📂 Directory Structure
```text
MemeGPT/
├── backend/            # FastAPI, ARQ Workers, SQLAlchemy
├── frontend/           # React + Vite + TypeScript
├── scripts/            # Deployment and maintenance scripts
└── docker-compose.yml  # Container orchestration
```

### 🛠️ Tech Stack
- **Backend**: Python 3.10+, FastAPI, ARQ (Redis Queue), PostgreSQL (SQLAlchemy), Alembic.
- **Frontend**: React, TypeScript, Vite, Tailwind CSS.
- **Infrastructure**: Redis (Cache/Queue), Cloudflare R2 (Object Storage), Sentry (Error Monitoring), Docker.

---

## 3. Getting Started

### Prerequisites
- **Runtimes**: Python 3.10+, Node.js 18+, Docker, Git.
- **API Keys**: OpenAI, Google Gemini, Stripe (Optional), Cloudflare R2 (Optional).

### Quick Setup (Local)

#### 1. Clone the Repository
```bash
git clone https://github.com/dhananjaylab/MemeGPT.git
cd MemeGPT
```

#### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # Configure your API keys
alembic upgrade head      # Run database migrations
uvicorn main:app --reload # Start FastAPI server on http://localhost:8000
```

#### 3. Worker Setup (Run in a separate terminal)
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python -m arq workers.meme_worker.WorkerSettings
```

#### 4. Frontend Setup (Run in a separate terminal)
```bash
cd frontend
npm install
npm run dev               # Start Vite dev server on http://localhost:5173
```

### Docker Setup

For a fully containerized environment, simply use Docker Compose:
```bash
docker-compose up -d
```
This will automatically spin up the FastAPI backend, ARQ worker, Redis, PostgreSQL, and frontend services.

---

## 4. Configuration & Rate Limiting

### Environment Variables
Configure your environment variables in `backend/.env`. See `backend/.env.example` for all available options.
- `DATABASE_URL`: PostgreSQL connection string.
- `REDIS_URL`: Redis connection string.
- `AI_PROVIDER`: `openai`, `gemini`, or `both` (enables automatic failover).
- `RATE_LIMIT_ENABLED`: Set to `true` to enable tiered rate limits.

### Rate Limit Tiers
Rate limits are enforced via a sliding window algorithm in Redis to prevent abuse and manage API quota.
- **Free Tier**: 10 requests/hour (2 requests/minute burst).
- **Pro Tier**: 500 requests/hour (50 requests/minute burst).
- **API Tier**: 1000 requests/hour (100 requests/minute burst).

---

## 5. Testing & Verification

### Local Template Testing
1. **Direct Access**: Check local frame serving at `http://localhost:8000/frames/Drake-Hotline-Bling.jpg`.
2. **API Check**: Verify `GET /api/memes/templates` returns valid JSON containing available templates.
3. **Seeding**: Use `POST /api/memes/seed-templates` to refresh or populate template data in the database.

### Automation & Unit Tests
- **Backend Testing**:
  ```bash
  cd backend
  pytest
  ```
- **Frontend Testing**:
  ```bash
  cd frontend
  npm test
  ```

---

## 6. Maintenance & Monitoring

### Daily Tasks
- **Health Checks**: Run `curl http://localhost:8000/api/health` to verify service uptime.
- **Log Review**: Inspect container logs for anomalies or errors:
  ```bash
  docker-compose logs --since 24h | grep -i error
  ```

### Periodic Maintenance
- **Database**: Run `VACUUM ANALYZE` weekly; clean up old completed `jobs` (>90 days) monthly.
- **Storage**: Clean temporary generated files in `/app/output` weekly.
- **Backups**: Use `pg_dump` for routine database backups and verify Cloudflare R2 backup integrity.

### Storage Maintenance
The `backend/public/` directory serves as fallback storage when Cloudflare R2 is unavailable or unconfigured.

- **Check Metrics**: `GET /api/storage/metrics`
- **Manual Cleanup**:
  ```bash
  # Delete files older than 7 days
  python scripts/cleanup_storage.py --cleanup-age --max-age-days 7
  # Reduce total fallback storage size to 500 MB
  python scripts/cleanup_storage.py --cleanup-size --max-size-mb 500
  ```
- **R2 Migration**: Migrate local fallback files to cloud storage:
  ```bash
  python scripts/cleanup_storage.py --migrate-to-r2
  ```
- **Automated Cleanup**: Add the following cron job to automate nightly cleanup:
  ```bash
  0 2 * * * python scripts/cleanup_storage.py --scheduled
  ```

### Monitoring
Monitor system resources to ensure CPU (<80%) and Memory (<85%) remain stable, and API response times stay below 500ms. Sentry integration provides real-time error tracking and exception alerting.

---

## 7. Troubleshooting

### Common Issues & Solutions
- **AI Formatting Failures**: Automatic field mapping and fallback parsing are handled transparently in `meme_ai.py`.
- **Template 404s**: Ensure Imgflip credentials are valid or verify that local fallback templates exist in `backend/public/frames`.
- **Provider Outages**: The system automatically fails over between OpenAI and Google Gemini if one API experiences downtime.
- **Rate Limited**: Check the `X-RateLimit-Remaining` headers in API responses and wait for the duration specified in `Retry-After`.

### Disaster Recovery
- **Database Restore**:
  ```bash
  pg_restore -d memegpt < backup.sql
  ```
- **System Restore**: Stop all running services, restore the database and storage directories, verify file integrity, and restart the containers.

---

## 8. Contributing & Support

We welcome contributions from the community!
- **Bugs & Issues**: Open an issue on GitHub with detailed reproduction steps.
- **Enhancements**: Pull requests are highly welcome for UI/UX improvements, AI prompt engineering, or adding new meme templates.
- **Support Inquiries**: Reach out to support@memegpt.dev or visit our [GitHub Issues](https://github.com/dhananjaylab/MemeGPT/issues) page.

---

## 9. License

This project is licensed under the MIT License. See the LICENSE file for details.

---

**Happy Meme Generation! 🎉**
