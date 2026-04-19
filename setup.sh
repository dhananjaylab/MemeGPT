#!/bin/bash

# MemeGPT v2 Setup Script
# This script helps set up the new MemeGPT v2 environment

set -e

echo "🧙 MemeGPT v2 Setup"
echo "==================="

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    echo "   Visit: https://nodejs.org/"
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version 18+ is required. Current version: $(node -v)"
    exit 1
fi

echo "✅ Node.js $(node -v) detected"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11+ first."
    exit 1
fi

echo "✅ Python $(python3 --version) detected"

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
npm install

# Create environment files if they don't exist
if [ ! -f .env.local ]; then
    echo "⚙️  Creating .env.local..."
    cp .env.local.example .env.local
    echo "   ✓ Created .env.local (please edit with your API keys)"
fi

if [ ! -f backend/.env ]; then
    echo "⚙️  Creating backend/.env..."
    cp backend/.env.example backend/.env
    echo "   ✓ Created backend/.env (please edit with your API keys)"
fi

# Check if Docker is available
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "🐳 Docker detected"
    echo ""
    echo "Choose your setup method:"
    echo "1) Docker (recommended - includes database and Redis)"
    echo "2) Local development (requires manual database setup)"
    echo ""
    read -p "Enter your choice (1 or 2): " choice
    
    case $choice in
        1)
            echo "🐳 Starting with Docker..."
            echo "   This will start PostgreSQL, Redis, backend, and frontend"
            echo "   Make sure to edit your .env files first!"
            echo ""
            echo "   To start: docker compose up --build"
            echo "   To stop:  docker compose down"
            ;;
        2)
            echo "💻 Local development setup..."
            setup_local_dev
            ;;
        *)
            echo "Invalid choice. Please run the script again."
            exit 1
            ;;
    esac
else
    echo "💻 Docker not found, setting up for local development..."
    setup_local_dev
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit your environment files:"
echo "   - .env.local (frontend settings)"
echo "   - backend/.env (backend settings, including OPENAI_API_KEY)"
echo ""
echo "2. Start the application:"
if command -v docker &> /dev/null; then
    echo "   Docker: docker compose up --build"
fi
echo "   Local:  npm run dev (frontend) + uvicorn backend.main:app --reload (backend)"
echo ""
echo "3. Visit http://localhost:3000"
echo ""
echo "📚 For detailed instructions, see README-v2.md"

function setup_local_dev() {
    echo "Setting up Python virtual environment..."
    
    # Create Python virtual environment
    if [ ! -d "backend/.venv" ]; then
        echo "🐍 Creating Python virtual environment..."
        cd backend
        python3 -m venv .venv
        cd ..
        echo "   ✓ Created backend/.venv"
    fi
    
    # Install Python dependencies
    echo "📦 Installing Python dependencies..."
    cd backend
    source .venv/bin/activate
    pip install -r requirements.txt
    cd ..
    echo "   ✓ Installed Python packages"
    
    echo ""
    echo "⚠️  You'll need to set up PostgreSQL and Redis manually:"
    echo "   Option 1: Use Docker for just the databases:"
    echo "   docker compose up postgres redis -d"
    echo ""
    echo "   Option 2: Install locally:"
    echo "   - PostgreSQL: https://postgresql.org/download/"
    echo "   - Redis: https://redis.io/download"
    echo ""
    echo "   Then update DATABASE_URL and REDIS_URL in backend/.env"
}