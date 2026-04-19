@echo off
echo 🧙 MemeGPT v2 Setup
echo ==================

REM Check if Node.js is installed
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js is not installed. Please install Node.js 18+ first.
    echo    Visit: https://nodejs.org/
    pause
    exit /b 1
)

echo ✅ Node.js detected: 
node --version

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed. Please install Python 3.11+ first.
    echo    Visit: https://python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python detected:
python --version

REM Install Node.js dependencies
echo 📦 Installing Node.js dependencies...
npm install
if %errorlevel% neq 0 (
    echo ❌ Failed to install Node.js dependencies
    pause
    exit /b 1
)

REM Create environment files if they don't exist
if not exist .env.local (
    echo ⚙️  Creating .env.local...
    copy .env.local.example .env.local
    echo    ✓ Created .env.local (please edit with your API keys)
)

if not exist backend\.env (
    echo ⚙️  Creating backend\.env...
    copy backend\.env.example backend\.env
    echo    ✓ Created backend\.env (please edit with your API keys)
)

REM Check if Docker is available
docker --version >nul 2>&1
if %errorlevel% equ 0 (
    echo 🐳 Docker detected
    echo.
    echo Choose your setup method:
    echo 1) Docker (recommended - includes database and Redis)
    echo 2) Local development (requires manual database setup)
    echo.
    set /p choice="Enter your choice (1 or 2): "
    
    if "!choice!"=="1" (
        echo 🐳 Starting with Docker...
        echo    This will start PostgreSQL, Redis, backend, and frontend
        echo    Make sure to edit your .env files first!
        echo.
        echo    To start: docker compose up --build
        echo    To stop:  docker compose down
    ) else if "!choice!"=="2" (
        call :setup_local_dev
    ) else (
        echo Invalid choice. Please run the script again.
        pause
        exit /b 1
    )
) else (
    echo 💻 Docker not found, setting up for local development...
    call :setup_local_dev
)

echo.
echo 🎉 Setup complete!
echo.
echo 📋 Next steps:
echo 1. Edit your environment files:
echo    - .env.local (frontend settings)
echo    - backend\.env (backend settings, including OPENAI_API_KEY)
echo.
echo 2. Start the application:
echo    Docker: docker compose up --build
echo    Local:  npm run dev (frontend) + uvicorn backend.main:app --reload (backend)
echo.
echo 3. Visit http://localhost:3000
echo.
echo 📚 For detailed instructions, see README-v2.md
pause
exit /b 0

:setup_local_dev
echo Setting up Python virtual environment...

REM Create Python virtual environment
if not exist backend\.venv (
    echo 🐍 Creating Python virtual environment...
    cd backend
    python -m venv .venv
    cd ..
    echo    ✓ Created backend\.venv
)

REM Install Python dependencies
echo 📦 Installing Python dependencies...
cd backend
call .venv\Scripts\activate.bat
pip install -r requirements.txt
cd ..
echo    ✓ Installed Python packages

echo.
echo ⚠️  You'll need to set up PostgreSQL and Redis manually:
echo    Option 1: Use Docker for just the databases:
echo    docker compose up postgres redis -d
echo.
echo    Option 2: Install locally:
echo    - PostgreSQL: https://postgresql.org/download/
echo    - Redis: https://redis.io/download
echo.
echo    Then update DATABASE_URL and REDIS_URL in backend\.env
goto :eof