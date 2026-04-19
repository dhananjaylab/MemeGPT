# 🧙 MemeGPT v2 - AI Meme Generator

> **Next.js 15 · FastAPI · ARQ · PostgreSQL · Cloudflare R2 · GPT-4o**

Transform any topic, story, or situation into viral memes with AI magic! ✨

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/Dhananjay-97/MemeGPT.git
cd MemeGPT

# Copy environment files
cp .env.local.example .env.local
cp backend/.env.example backend/.env

# Edit the environment files with your API keys
# At minimum, you need:
# - OPENAI_API_KEY in backend/.env
# - NEXT_PUBLIC_API_URL in .env.local

# Start all services
docker compose up --build

# Visit http://localhost:3000
```

### Option 2: Local Development

```bash
# Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Start PostgreSQL and Redis (via Docker)
docker compose up postgres redis -d

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn backend.main:app --reload --port 8000

# Start ARQ worker (in another terminal)
arq backend.workers.meme_worker.WorkerSettings

# Frontend setup (in another terminal)
npm install
npm run dev

# Visit http://localhost:3000
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Browser (Next.js 15)                                  │
│  - React 19, Tailwind CSS, shadcn/ui                   │
│  - Server-side rendering, OG image generation          │
└───────────────────┬─────────────────────────────────────┘
                    │ HTTP/WebSocket
┌───────────────────▼─────────────────────────────────────┐
│  FastAPI Backend                                        │
│  - Async endpoints, rate limiting, CORS                 │
│  - JWT auth, Stripe integration                         │
└──────────┬───────────────────────────┬──────────────────┘
           │ Redis (ARQ)               │ asyncpg
┌──────────▼──────────┐   ┌───────────▼──────────────────┐
│  ARQ Worker         │   │  PostgreSQL                  │
│  1. GPT-4o prompts  │   │  - Users, memes, jobs        │
│  2. PIL composition │   │  - Analytics, billing        │
│  3. R2 upload       │   └──────────────────────────────┘
│  4. DB persistence  │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Cloudflare R2      │
│  - Original images  │
│  - Thumbnails       │
└─────────────────────┘
```

## 🎯 Features

### Phase 1 - Foundation ✅
- [x] Next.js 15 frontend with React 19
- [x] FastAPI backend with async support
- [x] 50+ meme templates with accurate positioning
- [x] ARQ job queue for non-blocking generation
- [x] Cloudflare R2 storage integration
- [x] Mobile-first responsive design
- [x] Real-time generation progress

### Phase 2 - Growth Features 🚧
- [ ] NextAuth.js authentication (Google, GitHub)
- [ ] Personal meme history and galleries
- [ ] One-click social sharing (Twitter, Reddit, WhatsApp)
- [ ] Dynamic OG image generation
- [ ] Public meme permalinks
- [ ] Trending topics sidebar

### Phase 3 - Monetization 📋
- [ ] Public REST API with authentication
- [ ] Embeddable widget for developers
- [ ] Stripe subscription tiers
- [ ] Usage analytics dashboard
- [ ] Public meme gallery
- [ ] Developer portal

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Next.js 15, React 19 | Server-side rendering, routing |
| | Tailwind CSS, shadcn/ui | Styling, components |
| | NextAuth.js | Authentication |
| **Backend** | FastAPI, Python 3.11+ | API server, async processing |
| | SQLAlchemy, Alembic | Database ORM, migrations |
| | ARQ, Redis | Background job processing |
| **AI** | OpenAI GPT-4o | Meme text generation |
| | Claude (fallback) | Backup AI provider |
| **Storage** | Cloudflare R2 | Image storage, CDN |
| | PostgreSQL | Structured data |
| **Infrastructure** | Docker, Docker Compose | Containerization |
| | Vercel (frontend) | Frontend deployment |
| | Railway/Render (backend) | Backend deployment |

## 📁 Project Structure

```
memegpt-v2/
├── app/                    # Next.js app directory
│   ├── page.tsx           # Homepage
│   ├── meme/[id]/         # Meme permalink pages
│   ├── gallery/           # Public gallery
│   └── api/               # API routes (proxy to FastAPI)
├── components/            # React components
│   ├── MemeGenerator.tsx  # Main generation interface
│   ├── MemeCard.tsx       # Meme display component
│   └── TrendingTopics.tsx # Sidebar trending feed
├── lib/                   # Utilities and types
│   ├── api.ts            # API client
│   └── types.ts          # TypeScript definitions
├── backend/               # FastAPI backend
│   ├── main.py           # FastAPI app
│   ├── routers/          # API route handlers
│   ├── services/         # Business logic
│   ├── workers/          # ARQ background workers
│   └── models/           # Database models
├── templates/             # Meme template images
├── fonts/                # Font files for text rendering
└── meme_data.json        # Template definitions
```

## 🎨 Adding New Meme Templates

1. **Add the image**: Place the `.jpg` file in the `templates/` directory
2. **Update meme_data.json**: Add a new entry with:
   ```json
   {
     "id": 11,
     "name": "Your Meme Name",
     "file_path": "Your-Meme-File.jpg",
     "text_coordinates_xy_wh": [[x, y, width, height], ...],
     "usage_instructions": "How to use this meme...",
     // ... other fields
   }
   ```
3. **Test positioning**: Use the coordinate system where (0,0) is top-left
4. **Restart services**: Templates are loaded at startup

## 🚀 Deployment

### Frontend (Vercel)
```bash
# Connect your GitHub repo to Vercel
# Set environment variables in Vercel dashboard
# Deploy automatically on push to main
```

### Backend (Railway)
```bash
# Connect GitHub repo to Railway
# Set environment variables
# Deploy with Dockerfile
```

### Database & Redis
- **Railway**: PostgreSQL and Redis add-ons
- **Render**: PostgreSQL and Redis instances
- **AWS RDS**: For production PostgreSQL

### Storage (Cloudflare R2)
1. Create R2 bucket
2. Set CORS policy for frontend access
3. Configure environment variables

## 🔧 Configuration

### Required Environment Variables

**Frontend (.env.local)**:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_SECRET=your-secret-here
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

**Backend (backend/.env)**:
```bash
OPENAI_API_KEY=sk-your-openai-key
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
REDIS_URL=redis://localhost:6379/0
R2_ACCESS_KEY_ID=your-r2-key
R2_SECRET_ACCESS_KEY=your-r2-secret
STRIPE_SECRET_KEY=sk_test_your-stripe-key
```

## 📊 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

```bash
# Generate memes
POST /api/memes/generate
{
  "prompt": "When you realize it's Monday morning",
  "max_memes": 3
}

# Get job status
GET /api/jobs/{job_id}

# List public memes
GET /api/memes?page=1&limit=20&sort=recent

# Get trending topics
GET /api/trending
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Add tests if applicable
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for GPT-4o
- Vercel for Next.js and hosting
- The meme community for inspiration
- All contributors and users

---

**Made with ❤️ by the MemeGPT team**

[Website](https://memegpt.ai) • [Twitter](https://twitter.com/memegpt) • [GitHub](https://github.com/Dhananjay-97/MemeGPT)