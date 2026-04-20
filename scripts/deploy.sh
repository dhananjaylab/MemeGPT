#!/bin/bash
# Deployment Script for MemeGPT
# Handles application deployment to production/staging

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-staging}
DEPLOY_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
LOG_FILE="${DEPLOY_DIR}/deployment.log"

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Validate environment
validate_environment() {
    log "Validating deployment environment: $ENVIRONMENT"
    
    if [ "$ENVIRONMENT" != "production" ] && [ "$ENVIRONMENT" != "staging" ] && [ "$ENVIRONMENT" != "development" ]; then
        error "Invalid environment. Must be 'production', 'staging', or 'development'"
    fi
    
    # Check required files
    local required_files=(
        "backend/.env.${ENVIRONMENT}"
        "docker-compose.yml"
        "backend/requirements.txt"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$DEPLOY_DIR/$file" ]; then
            warning "Missing file: $file"
        fi
    done
    
    log "Environment validation complete"
}

# Build Docker images
build_images() {
    log "Building Docker images for $ENVIRONMENT environment..."
    
    cd "$DEPLOY_DIR"
    
    docker-compose --profile monitoring build \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        backend worker frontend
    
    log "Docker images built successfully"
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    cd "$DEPLOY_DIR"
    
    docker-compose run --rm backend python -m alembic upgrade head
    
    if [ $? -eq 0 ]; then
        log "Database migrations completed successfully"
    else
        error "Database migrations failed"
    fi
}

# Start services
start_services() {
    log "Starting services..."
    
    cd "$DEPLOY_DIR"
    
    docker-compose up -d postgres redis backend worker
    
    # Wait for backend to be healthy
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose exec backend curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
            log "Backend service is healthy"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    
    error "Backend service failed to become healthy within timeout"
}

# Run health checks
run_health_checks() {
    log "Running health checks..."
    
    cd "$DEPLOY_DIR"
    
    # Check backend
    if docker-compose exec backend curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
        log "Backend health check: PASS"
    else
        error "Backend health check failed"
    fi
    
    # Check database
    if docker-compose exec postgres pg_isready -U memegpt -d memegpt > /dev/null 2>&1; then
        log "Database health check: PASS"
    else
        error "Database health check failed"
    fi
    
    # Check Redis
    if docker-compose exec redis redis-cli ping > /dev/null 2>&1; then
        log "Redis health check: PASS"
    else
        error "Redis health check failed"
    fi
    
    log "All health checks passed"
}

# Backup database
backup_database() {
    log "Creating database backup..."
    
    local backup_dir="${DEPLOY_DIR}/backups"
    mkdir -p "$backup_dir"
    
    local backup_file="$backup_dir/db_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    docker-compose exec -T postgres pg_dump \
        -U memegpt -d memegpt \
        > "$backup_file"
    
    if [ $? -eq 0 ]; then
        log "Database backup created: $backup_file"
    else
        warning "Database backup failed"
    fi
}

# Cleanup old containers
cleanup_old_containers() {
    log "Cleaning up old containers..."
    
    docker-compose down -v
    
    log "Cleanup complete"
}

# Deploy
deploy() {
    log "Starting deployment for $ENVIRONMENT environment..."
    
    validate_environment
    backup_database
    
    if [ "$ENVIRONMENT" == "production" ]; then
        log "PRODUCTION DEPLOYMENT - Additional safety checks enabled"
        cleanup_old_containers
    fi
    
    build_images
    start_services
    run_migrations
    run_health_checks
    
    log "Deployment completed successfully!"
    log "Frontend: http://localhost:3000"
    log "API: http://localhost:8000"
    log "API Docs: http://localhost:8000/docs"
}

# Rollback
rollback() {
    log "Rolling back deployment..."
    
    cd "$DEPLOY_DIR"
    docker-compose down
    
    warning "Rollback complete. Services stopped."
}

# Main
main() {
    case "${2:-deploy}" in
        deploy)
            deploy
            ;;
        rollback)
            rollback
            ;;
        healthcheck)
            run_health_checks
            ;;
        *)
            echo "Usage: $0 {production|staging|development} {deploy|rollback|healthcheck}"
            exit 1
            ;;
    esac
}

main "$@"
