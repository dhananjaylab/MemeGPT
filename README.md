# 🧙 MemeGPT - Your Personal Meme Generator

Generate hilarious memes with ease using MemeGPT! This application leverages the power of OpenAI's GPT models to create memes based on your text input. Simply provide a situation, topic, or story, and MemeGPT will intelligently select relevant meme templates and generate meme images with appropriate captions.

![MemeGPT Demo](https://your-demo-image-or-gif-url.com) <!-- Optional: Add your demo screenshot or GIF -->

---

## 📚 Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Development Setup](#development-setup)
  - [Docker Setup](#docker-setup)
- [Architecture](#architecture)
- [API Documentation](#api-documentation)
- [Configuration](#configuration)
- [How to Use](#how-to-use)
  - [Generating Memes](#generating-memes)
- [Deployment](#deployment)
- [Contributing](#contributing)

---

## Features

- **AI-Powered Meme Generation**  
  Uses OpenAI's GPT-4o models to understand your input and generate relevant meme text.

- **Variety of Meme Templates**  
  Comes pre-loaded with a selection of popular meme templates (Drake Hotline Bling, Distracted Boyfriend, Disaster Girl, and more!).

- **Modern Web Interface**  
  Built with React + TypeScript and Vite for a responsive and intuitive user experience.

- **Async Job Processing**  
  ARQ-powered job queue for non-blocking meme generation with real-time progress tracking.

- **Advanced Image Management**  
  Cloudflare R2 storage integration for optimized image delivery and CDN caching.

- **Rate Limiting & Billing**  
  Integrated Stripe payments with subscription tiers and sliding window rate limiting.

- **Production-Ready**  
  Docker containerization, comprehensive error handling, and monitoring with Sentry.

---

## Quick Start

### Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+** - [Download here](https://www.python.org/downloads/)
- **Node.js 18+** - [Download here](https://nodejs.org/)
- **Docker & Docker Compose** (for containerized setup) - [Download here](https://www.docker.com/products/docker-desktop)
- **Git** - [Download here](https://git-scm.com/)

#### API Keys Required

- **OpenAI API Key** - Get from [OpenAI Platform](https://platform.openai.com/)
- **Gemini API Key** - Get from [Google AI Studio](https://aistudio.google.com/)
- **Stripe API Key** (optional) - Get from [Stripe Dashboard](https://dashboard.stripe.com)
- **Cloudflare R2 Credentials** (optional) - Get from [Cloudflare Dashboard](https://dash.cloudflare.com)

### Development Setup

#### 1. Clone and Setup Backend

```bash
# Clone the repository
git clone https://github.com/your-repo/MemeGPT.git
cd MemeGPT

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install backend dependencies
cd backend
pip install -r requirements.txt
```

#### 2. Setup Environment Variables

Create a `.env` file in the root directory:

```env
# ─── Database Configuration ───
DATABASE_URL=postgresql://memegpt:password@localhost:5432/memegpt

# ─── Redis Configuration ───
REDIS_URL=redis://localhost:6379

# ─── API Keys ───
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
AI_PROVIDER=openai  # Options: openai, gemini, both
STRIPE_SECRET_KEY=your_stripe_secret_key_here
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key_here

# ─── Security ───
SECRET_KEY=your_secret_key_here_change_in_production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ─── CORS Configuration ───
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# ─── Cloud Storage (Optional) ───
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_ACCESS_KEY_ID=your_access_key
CLOUDFLARE_SECRET_ACCESS_KEY=your_secret_key
R2_BUCKET_NAME=memegpt-images

# ─── Monitoring (Optional) ───
SENTRY_DSN=your_sentry_dsn_here
```

#### 3. Setup PostgreSQL and Redis

**Option A: Local Installation**
```bash
# macOS (using Homebrew)
brew install postgresql redis

# Start services
brew services start postgresql
brew services start redis

# Create database
createdb memegpt
```

**Option B: Docker Containers**
```bash
docker run --name memegpt-postgres -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres:15-alpine
docker run --name memegpt-redis -p 6379:6379 -d redis:7-alpine
```

#### 4. Run Database Migrations

```bash
cd backend

# Create alembic migrations
alembic upgrade head

# Or create tables directly
python -c "from app.db.session import engine, Base; Base.metadata.create_all(engine)"
```

#### 5. Start Backend Services

In separate terminal windows:

```bash
# Terminal 1: Start FastAPI server
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start ARQ worker
cd backend
python -m arq workers.main
```

#### 6. Setup and Run Frontend

```bash
# In a new terminal, from project root
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Your application is now running:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc

### Docker Setup

For quick setup using Docker Compose:

```bash
# From project root
docker-compose up -d

# Check services
docker-compose ps

# View logs
docker-compose logs -f

# Shutdown
docker-compose down
```

The `docker-compose.yml` includes:
- PostgreSQL database (port 5432)
- Redis cache (port 6379)
- FastAPI backend (port 8000)
- ARQ worker

**Note**: Update environment variables in `.env` file or `docker-compose.yml` for your configuration.

---

## Architecture

```
MemeGPT/
├── backend/
│   ├── main.py                 # FastAPI application entry
│   ├── routers/               # API route handlers
│   │   ├── auth.py           # Authentication endpoints
│   │   ├── memes.py          # Meme generation endpoints
│   │   ├── jobs.py           # Job status endpoints
│   │   ├── users.py          # User management
│   │   ├── stripe.py         # Billing integration
│   │   ├── trending.py       # Trending memes
│   │   └── health.py         # Health checks
│   ├── services/             # Business logic
│   ├── db/                   # Database layer
│   ├── models/               # SQLAlchemy models
│   ├── core/                 # Configuration & middleware
│   └── workers/              # ARQ job handlers
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/           # Page components
│   │   ├── lib/             # Utilities & API client
│   │   └── App.tsx          # Main App component
│   ├── index.html           # HTML template
│   └── vite.config.ts       # Vite configuration
└── docker-compose.yml        # Multi-container orchestration
```

---

## API Documentation

For comprehensive API documentation, see [API_DOCUMENTATION.md](./API_DOCUMENTATION.md).

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | User authentication |
| `POST` | `/api/memes/generate` | Create new meme |
| `GET` | `/api/jobs/{job_id}` | Get job status |
| `GET` | `/api/memes/{meme_id}` | Retrieve meme |
| `GET` | `/api/trending` | Get trending memes |

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `REDIS_URL` | ✅ | Redis connection string |
| `OPENAI_API_KEY` | ❌*| OpenAI API key for GPT models (*either OpenAI or Gemini required) |
| `GEMINI_API_KEY` | ❌*| Google Gemini API key (*either OpenAI or Gemini required) |
| `AI_PROVIDER` | ❌ | AI model provider to use (`openai`, `gemini`, or `both`) |
| `SECRET_KEY` | ✅ | JWT signing key (change in production!) |
| `CORS_ORIGINS` | ✅ | Allowed frontend origins |
| `STRIPE_SECRET_KEY` | ❌ | Stripe API key (optional) |
| `SENTRY_DSN` | ❌ | Error tracking (optional) |

### Rate Limiting

Rate limits are configured per subscription tier:

| Tier | Limit | Window |
|------|-------|--------|
| Free | 10 | 1 hour |
| Pro | 100 | 1 hour |
| Enterprise | Unlimited | — |

---

## How to Use

### Generating Memes

1. **Navigate to the Dashboard**
   - Open http://localhost:5173 in your browser
   - Login or signup for an account

2. **Enter Your Meme Prompt**
   - Type or paste text describing the situation/topic

3. **Generate Meme**
   - Click "Generate Meme" button
   - Wait for AI to process and select template

4. **View and Share**
   - Download the generated meme image
   - Share directly to social media

---

## Deployment

### Production Deployment

For production deployment, see [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md).

#### Key Considerations

1. **Environment Variables**: Update all secrets for production
2. **Database**: Use managed PostgreSQL service (AWS RDS, Heroku Postgres)
3. **Cache**: Use managed Redis service (AWS ElastiCache, Heroku Redis)
4. **SSL/TLS**: Enable HTTPS with valid certificates
5. **Monitoring**: Setup Sentry and logging aggregation
6. **Backups**: Configure automated database backups

#### Docker Production Build

```bash
docker build -f backend/Dockerfile -t memegpt-backend:latest backend/
docker build -f frontend/Dockerfile -t memegpt-frontend:latest frontend/
```

---

## Contributing

We welcome contributions! Please follow these guidelines:

### 🧠 Improve AI Prompts

Help refine the instructions in `system_instructions.py` to generate even better meme text.

### 💡 Suggest New Meme Templates

Propose new meme formats to be added to the template database.

### 🎨 Enhance UI/UX

Suggest or implement improvements to the React interface.

### 🐛 Report Bugs

Found a bug? Please [open an issue](https://github.com/your-repo/MemeGPT/issues) with:
- Description of the bug
- Steps to reproduce
- Expected vs actual behavior

### 📝 Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or feedback:
- Open an [issue](https://github.com/your-repo/MemeGPT/issues)
- Email: support@memegpt.dev

---

**Happy Meme Generation! 🎉**   
