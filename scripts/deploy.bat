@echo off
REM Deployment Script for MemeGPT (Windows)
REM Handles application deployment to production/staging

setlocal enabledelayedexpansion
set ENVIRONMENT=%1
set ACTION=%2

if "!ENVIRONMENT!"=="" set ENVIRONMENT=staging
if "!ACTION!"=="" set ACTION=deploy

set DEPLOY_DIR=%~dp0..
set LOG_FILE=!DEPLOY_DIR!\deployment.log

REM Colors (using text formatting)
echo.

call :log "Starting MemeGPT Deployment Script"
call :log "Environment: !ENVIRONMENT!"
call :log "Action: !ACTION!"

REM Validate environment
call :validate_environment

REM Execute action
if "!ACTION!"=="deploy" (
    call :deploy
) else if "!ACTION!"=="rollback" (
    call :rollback
) else if "!ACTION!"=="healthcheck" (
    call :run_health_checks
) else (
    echo Usage: deploy.bat [production^|staging^|development] [deploy^|rollback^|healthcheck]
    exit /b 1
)

goto :end

:log
setlocal
set message=%~1
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a:%%b)
echo [!mydate! !mytime!] !message! >> "!LOG_FILE!"
echo [!mydate! !mytime!] !message!
endlocal
exit /b 0

:validate_environment
if "!ENVIRONMENT!"=="production" (
    call :log "Production deployment mode enabled"
    goto :validate_environment_end
)
if "!ENVIRONMENT!"=="staging" (
    call :log "Staging deployment mode enabled"
    goto :validate_environment_end
)
if "!ENVIRONMENT!"=="development" (
    call :log "Development deployment mode enabled"
    goto :validate_environment_end
)
call :error "Invalid environment. Must be 'production', 'staging', or 'development'"
:validate_environment_end
exit /b 0

:backup_database
call :log "Creating database backup..."
if not exist "!DEPLOY_DIR!\backups" mkdir "!DEPLOY_DIR!\backups"

for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)
set backup_file=!DEPLOY_DIR!\backups\db_backup_!mydate!_!mytime!.sql

docker-compose exec -T postgres pg_dump -U memegpt -d memegpt > "!backup_file!"
if !errorlevel! equ 0 (
    call :log "Database backup created: !backup_file!"
) else (
    call :warning "Database backup failed"
)
exit /b 0

:build_images
call :log "Building Docker images..."
cd /d "!DEPLOY_DIR!"
docker-compose build --build-arg BUILDKIT_INLINE_CACHE=1 backend worker frontend
if !errorlevel! neq 0 call :error "Docker build failed"
call :log "Docker images built successfully"
exit /b 0

:run_migrations
call :log "Running database migrations..."
cd /d "!DEPLOY_DIR!"
docker-compose run --rm backend python -m alembic upgrade head
if !errorlevel! neq 0 call :error "Database migrations failed"
call :log "Database migrations completed successfully"
exit /b 0

:start_services
call :log "Starting services..."
cd /d "!DEPLOY_DIR!"
docker-compose up -d postgres redis backend worker

REM Wait for backend to be healthy
set max_attempts=30
set attempt=0

:wait_backend
if !attempt! geq !max_attempts! (
    call :error "Backend service failed to become healthy within timeout"
)

docker-compose exec backend curl -f http://localhost:8000/api/health > nul 2>&1
if !errorlevel! equ 0 (
    call :log "Backend service is healthy"
    exit /b 0
)

set /a attempt=!attempt!+1
timeout /t 2 /nobreak > nul
echo.
goto wait_backend

:run_health_checks
call :log "Running health checks..."
cd /d "!DEPLOY_DIR!"

REM Check backend
docker-compose exec backend curl -f http://localhost:8000/api/health > nul 2>&1
if !errorlevel! equ 0 (
    call :log "Backend health check: PASS"
) else (
    call :error "Backend health check failed"
)

REM Check database
docker-compose exec postgres pg_isready -U memegpt -d memegpt > nul 2>&1
if !errorlevel! equ 0 (
    call :log "Database health check: PASS"
) else (
    call :error "Database health check failed"
)

REM Check Redis
docker-compose exec redis redis-cli ping > nul 2>&1
if !errorlevel! equ 0 (
    call :log "Redis health check: PASS"
) else (
    call :error "Redis health check failed"
)

call :log "All health checks passed"
exit /b 0

:deploy
call :log "Starting deployment for !ENVIRONMENT! environment..."
call :validate_environment
call :backup_database

if "!ENVIRONMENT!"=="production" (
    call :log "PRODUCTION DEPLOYMENT - Additional safety checks enabled"
    cd /d "!DEPLOY_DIR!"
    docker-compose down -v
)

call :build_images
call :start_services
call :run_migrations
call :run_health_checks

call :log "Deployment completed successfully!"
call :log "Frontend: http://localhost:3000"
call :log "API: http://localhost:8000"
call :log "API Docs: http://localhost:8000/docs"
exit /b 0

:rollback
call :log "Rolling back deployment..."
cd /d "!DEPLOY_DIR!"
docker-compose down
call :warning "Rollback complete. Services stopped."
exit /b 0

:error
call :log "ERROR: %~1"
exit /b 1

:warning
call :log "WARNING: %~1"
exit /b 0

:end
endlocal
