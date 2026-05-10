# Backend Public Directory Usage Guide

Quick reference for working with the `backend/public/` directory.

## Directory Purpose

The `backend/public/` directory serves as **fallback storage** for generated memes when Cloudflare R2 is unavailable.

## Quick Start

### Check Storage Status

```bash
# View current storage metrics
curl http://localhost:8000/api/storage/metrics
```

### Manual Cleanup

```bash
# Preview what would be deleted (dry run)
python scripts/cleanup_storage.py --cleanup-age --dry-run

# Actually delete files older than 7 days
python scripts/cleanup_storage.py --cleanup-age

# Delete oldest files until size is below 500 MB
python scripts/cleanup_storage.py --cleanup-size --max-size-mb 500
```

### Automated Cleanup (Cron)

Add to crontab for daily cleanup at 2 AM:

```bash
0 2 * * * cd /path/to/MemeGPT && python scripts/cleanup_storage.py --scheduled
```

## API Endpoints

### GET /api/storage/metrics
Get current storage statistics.

**Response:**
```json
{
  "exists": true,
  "file_count": 42,
  "total_size_mb": 125.5,
  "oldest_file_age_hours": 168.5,
  "newest_file_age_hours": 0.5,
  "average_file_size_kb": 3072.5
}
```

### POST /api/storage/cleanup/age
Remove files older than specified age.

**Request:**
```json
{
  "max_age_days": 7,
  "dry_run": true
}
```

**Response:**
```json
{
  "deleted_count": 15,
  "freed_mb": 45.2,
  "dry_run": true,
  "errors": []
}
```

### POST /api/storage/cleanup/size
Remove oldest files until size target is met.

**Request:**
```json
{
  "target_size_mb": 500,
  "dry_run": false
}
```

### POST /api/storage/migrate-to-r2
Migrate local files to R2 storage.

**Request:**
```json
{
  "delete_after_upload": false
}
```

### POST /api/storage/cleanup/scheduled
Run the full scheduled cleanup routine.

## Common Tasks

### Monitor Storage Growth

```bash
# Check metrics every hour
watch -n 3600 'curl -s http://localhost:8000/api/storage/metrics | jq'
```

### Emergency Cleanup

If disk space is critically low:

```bash
# Immediately delete files older than 3 days
python scripts/cleanup_storage.py --cleanup-age --max-age-days 3

# Then reduce size to 100 MB
python scripts/cleanup_storage.py --cleanup-size --max-size-mb 100
```

### Migrate to R2

When R2 is configured and you want to move existing files:

```bash
# Migrate without deleting local copies
python scripts/cleanup_storage.py --migrate-to-r2

# Migrate and delete local files after successful upload
python scripts/cleanup_storage.py --migrate-to-r2 --delete-after-migration
```

## Troubleshooting

### Problem: Disk space full

**Solution:**
```bash
# Emergency cleanup - delete files older than 1 day
python scripts/cleanup_storage.py --cleanup-age --max-age-days 1

# Or reduce to minimal size
python scripts/cleanup_storage.py --cleanup-size --max-size-mb 50
```

### Problem: R2 is down, local storage filling up

**Solution:**
1. Increase cleanup frequency temporarily
2. Reduce max age threshold
3. Monitor R2 status and restore when available

### Problem: Files not being cleaned up automatically

**Solution:**
1. Check if cron job is running: `crontab -l`
2. Check cron logs: `grep CRON /var/log/syslog`
3. Run manual cleanup: `python scripts/cleanup_storage.py --scheduled`

## Best Practices

1. **Set up automated cleanup** - Don't rely on manual intervention
2. **Monitor storage metrics** - Set up alerts for high usage
3. **Use R2 as primary** - Local storage is only a fallback
4. **Regular migrations** - Move files to R2 when it's available
5. **Test dry runs first** - Always preview deletions before executing

## Configuration

Default settings in [`storage_cleanup.py`](../services/storage_cleanup.py):

- **Max Age**: 7 days
- **Max Size**: 1000 MB
- **Output Directory**: `backend/public/output/`

Override via script arguments or API requests.

## Security Notes

- Files in `output/` are **publicly accessible** via `/output/{filename}`
- No authentication required for static file access
- Only PNG files should be stored here
- Implement rate limiting on storage endpoints for production

## Performance Impact

- **Cleanup operations** are I/O intensive
- **Run during low-traffic periods** (e.g., 2-4 AM)
- **Dry runs** have minimal impact
- **R2 migration** can be slow for many files

## Related Documentation

- [Main README](README.md) - Detailed technical documentation
- [Storage Service](../services/storage.py) - R2 and local storage implementation
- [Storage Cleanup Service](../services/storage_cleanup.py) - Cleanup utilities
- [Storage Router](../routers/storage.py) - API endpoints