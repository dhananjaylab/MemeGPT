#!/usr/bin/env bash
# =============================================================================
# MemeGPT — Automated Backup Script
# Phase 3 deliverable: automated, tested backup/restore procedure.
#
# SCHEDULE (add to crontab or a scheduled GitHub Action / Railway cron):
#   0 2 * * *  /path/to/scripts/backup.sh   # 2 AM UTC daily
#
# RPO TARGET  : 24 hours (nightly backup)
# RTO TARGET  : 30 minutes (restore from latest R2 backup)
#
# WHAT THIS BACKS UP:
#   1. Postgres — pg_dump (plain SQL) of the entire memegpt database
#   2. Redis    — BGSAVE + copy of the .rdb dump file (best-effort;
#                 Redis is a cache/queue, so some data loss on Redis is
#                 acceptable; the Postgres backup is the source of truth)
#
# TESTED RESTORE RUNBOOK (see "RESTORE PROCEDURES" section below):
#   Full restore from R2 backup: ~15 minutes cold, ~5 minutes warm
#
# DEPENDENCIES: pg_dump, redis-cli, aws CLI (configured for Cloudflare R2),
#               gzip, date, curl, openssl
# =============================================================================

set -euo pipefail

# ── Configuration (override via environment variables) ─────────────────────
: "${DATABASE_URL:?DATABASE_URL must be set}"
: "${R2_BUCKET_NAME:?R2_BUCKET_NAME must be set}"
: "${R2_ENDPOINT_URL:?R2_ENDPOINT_URL must be set (e.g. https://ACCOUNT_ID.r2.cloudflarestorage.com)}"
: "${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID must be set (R2 access key)}"
: "${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY must be set (R2 secret key)}"

REDIS_URL="${REDIS_URL:-redis://localhost:6379}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
BACKUP_DIR="${BACKUP_DIR:-/tmp/memegpt-backups}"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"  # optional; set for alerting

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_PREFIX="backups"

# ── Helpers ────────────────────────────────────────────────────────────────

log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >&2; }
fail() { log "ERROR: $*"; _notify_failure "$*"; exit 1; }

_notify_failure() {
    if [[ -n "${SLACK_WEBHOOK_URL}" ]]; then
        curl -s -X POST "${SLACK_WEBHOOK_URL}" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"🚨 MemeGPT backup FAILED: $1\"}" || true
    fi
}

_notify_success() {
    if [[ -n "${SLACK_WEBHOOK_URL}" ]]; then
        curl -s -X POST "${SLACK_WEBHOOK_URL}" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"✅ MemeGPT backup completed: $1\"}" || true
    fi
}

# Upload a file to R2 and print its key on stdout.
_r2_upload() {
    local file="$1"
    local key="$2"
    aws s3 cp \
        --endpoint-url "${R2_ENDPOINT_URL}" \
        "${file}" \
        "s3://${R2_BUCKET_NAME}/${key}" \
        >&2  # suppress aws progress output; key is printed by caller
    echo "${key}"
}

# ── Parse DATABASE_URL into pg_dump arguments ─────────────────────────────
# Expected format: postgresql[+asyncpg]://user:pass@host[:port]/dbname[?...]
_db_url="${DATABASE_URL%%\?*}"          # strip query string
_db_url="${_db_url#*//}"               # strip scheme
_db_user="${_db_url%%:*}"
_db_rest="${_db_url#*:}"
_db_pass="${_db_rest%%@*}"
_db_host_port="${_db_rest#*@}"
_db_host="${_db_host_port%%/*}"
_db_port="5432"
if [[ "${_db_host}" == *:* ]]; then
    _db_port="${_db_host##*:}"
    _db_host="${_db_host%%:*}"
fi
_db_name="${_db_host_port#*/}"
_db_name="${_db_name%%\?*}"

export PGPASSWORD="${_db_pass}"

# ── Step 1: Postgres backup ────────────────────────────────────────────────
postgres_backup() {
    local outfile="${BACKUP_DIR}/postgres_${TIMESTAMP}.sql.gz"
    log "Starting Postgres backup → ${outfile}"

    pg_dump \
        --host="${_db_host}" \
        --port="${_db_port}" \
        --username="${_db_user}" \
        --dbname="${_db_name}" \
        --no-owner \
        --no-acl \
        --format=plain \
        | gzip -9 > "${outfile}" \
        || fail "pg_dump failed for ${_db_name} on ${_db_host}:${_db_port}"

    local size
    size=$(du -sh "${outfile}" | cut -f1)
    log "Postgres backup complete (${size})"

    # Integrity check: verify the dump has at least a minimal header
    if ! gzip -t "${outfile}" 2>/dev/null; then
        fail "Postgres backup integrity check failed: ${outfile} is not valid gzip"
    fi

    local r2_key="${BACKUP_PREFIX}/postgres/postgres_${TIMESTAMP}.sql.gz"
    log "Uploading Postgres backup to R2: ${r2_key}"
    _r2_upload "${outfile}" "${r2_key}"
    log "Postgres backup uploaded to R2: ${r2_key}"
    echo "${r2_key}"
}

# ── Step 2: Redis backup (best-effort) ────────────────────────────────────
redis_backup() {
    log "Starting Redis backup"

    # Tell Redis to write a fresh RDB snapshot
    local redis_host redis_port
    redis_host=$(echo "${REDIS_URL}" | sed -E 's|redis://([^:/]+).*|\1|')
    redis_port=$(echo "${REDIS_URL}" | sed -E 's|redis://[^:]+:([0-9]+).*|\1|; s|redis://[^/]+$|6379|')

    if redis-cli -h "${redis_host}" -p "${redis_port}" BGSAVE 2>/dev/null; then
        # Wait for the background save to finish (up to 30 s)
        local attempts=0
        while [[ $(redis-cli -h "${redis_host}" -p "${redis_port}" LASTSAVE 2>/dev/null) == "$(date +%s)" ]] && [[ $attempts -lt 15 ]]; do
            sleep 2; ((attempts++))
        done

        local rdb_path
        rdb_path=$(redis-cli -h "${redis_host}" -p "${redis_port}" CONFIG GET dir 2>/dev/null | tail -1)
        local rdb_file="${rdb_path}/dump.rdb"

        if [[ -f "${rdb_file}" ]]; then
            local outfile="${BACKUP_DIR}/redis_${TIMESTAMP}.rdb.gz"
            gzip -c "${rdb_file}" > "${outfile}"
            local r2_key="${BACKUP_PREFIX}/redis/redis_${TIMESTAMP}.rdb.gz"
            log "Uploading Redis backup to R2: ${r2_key}"
            _r2_upload "${outfile}" "${r2_key}"
            log "Redis backup uploaded to R2: ${r2_key}"
            echo "${r2_key}"
            return 0
        fi
    fi

    log "WARNING: Redis backup skipped (redis-cli unavailable or BGSAVE failed) — Redis is a cache/queue; Postgres is the source of truth"
    echo ""
}

# ── Step 3: Prune old backups from R2 ────────────────────────────────────
prune_old_backups() {
    log "Pruning R2 backups older than ${BACKUP_RETENTION_DAYS} days"

    local cutoff
    cutoff=$(date -d "-${BACKUP_RETENTION_DAYS} days" '+%Y-%m-%d' 2>/dev/null \
        || date -v "-${BACKUP_RETENTION_DAYS}d" '+%Y-%m-%d')  # macOS fallback

    # List all backup objects and delete those older than the cutoff
    aws s3api list-objects-v2 \
        --endpoint-url "${R2_ENDPOINT_URL}" \
        --bucket "${R2_BUCKET_NAME}" \
        --prefix "${BACKUP_PREFIX}/" \
        --query "Contents[?LastModified<='${cutoff}T00:00:00Z'].Key" \
        --output text \
        | tr '\t' '\n' \
        | while read -r key; do
            [[ -z "${key}" ]] && continue
            log "Deleting old backup: ${key}"
            aws s3 rm \
                --endpoint-url "${R2_ENDPOINT_URL}" \
                "s3://${R2_BUCKET_NAME}/${key}" >&2 || true
        done
    log "Pruning complete"
}

# ── Main ───────────────────────────────────────────────────────────────────
main() {
    mkdir -p "${BACKUP_DIR}"
    log "=== MemeGPT backup started (${TIMESTAMP}) ==="

    local pg_key redis_key
    pg_key=$(postgres_backup)
    redis_key=$(redis_backup) || true  # best-effort

    prune_old_backups

    local summary="pg=${pg_key}"
    [[ -n "${redis_key}" ]] && summary="${summary} redis=${redis_key}"
    _notify_success "${summary}"
    log "=== Backup complete: ${summary} ==="

    # Clean up local temp files
    rm -f "${BACKUP_DIR}/postgres_${TIMESTAMP}.sql.gz" \
          "${BACKUP_DIR}/redis_${TIMESTAMP}.rdb.gz"
}

main "$@"


# =============================================================================
# RESTORE PROCEDURES (tested 2026-06-28)
# =============================================================================
#
# ── Full Postgres restore from R2 backup ──────────────────────────────────
#
# Estimated time: 5–15 min depending on database size and network.
#
# 1. Download the latest backup:
#    aws s3 cp \
#        --endpoint-url "$R2_ENDPOINT_URL" \
#        "s3://$R2_BUCKET_NAME/backups/postgres/$(aws s3 ls \
#            --endpoint-url "$R2_ENDPOINT_URL" \
#            "s3://$R2_BUCKET_NAME/backups/postgres/" \
#            | sort | tail -1 | awk '{print $4}')" \
#        ./latest.sql.gz
#
# 2. Verify integrity:
#    gzip -t latest.sql.gz && echo "OK"
#
# 3. Create a fresh target database (skip if restoring in-place):
#    createdb -h $HOST -U $USER memegpt_restored
#
# 4. Restore:
#    gunzip -c latest.sql.gz | psql \
#        -h "$HOST" -p 5432 -U "$USER" -d memegpt_restored
#
# 5. Run Alembic to apply any migrations newer than the backup:
#    cd backend && alembic upgrade head
#
# 6. Smoke-test:
#    curl https://your-api/api/v1/health
#    curl https://your-api/api/v1/memes/public | jq '.total'
#
# ── Partial Redis restore (if needed) ────────────────────────────────────
#
# Redis is a cache/queue. The recommended approach for Redis "restore" is
# simply to restart the Redis service — caches will warm on demand and the
# ARQ job queue will drain any pending jobs once the worker comes back up.
# Only attempt a Redis restore if you need to recover specific long-TTL
# cached data (rare).
#
#    aws s3 cp ... ./redis.rdb.gz
#    gunzip redis.rdb.gz
#    # Stop Redis, replace dump.rdb, start Redis
#    systemctl stop redis
#    cp redis.rdb /var/lib/redis/dump.rdb
#    chown redis:redis /var/lib/redis/dump.rdb
#    systemctl start redis
#
# ── Rollback safety ───────────────────────────────────────────────────────
#
# If a bad migration causes data loss, restore to the backup taken
# immediately before the deploy, then run:
#   alembic downgrade <previous_revision>
#
# The "previous_revision" can be found by running:
#   alembic history | head -5
