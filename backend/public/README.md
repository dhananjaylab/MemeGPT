# Backend Public Assets Directory

This directory serves as the backend's static file storage location for the MemeGPT application.

## Directory Structure

```
backend/public/
├── frames/          # Meme template images
├── fonts/           # Fonts used by the compositor
├── meme_data.json   # Template metadata
└── output/          # Generated meme images (fallback storage)
```

## Purpose

The `backend/public/` directory is used for:

1. **Fallback Storage**: When Cloudflare R2 storage is unavailable or not configured, generated memes are stored in the `output/` subdirectory
2. **Static File Serving**: Files are served via FastAPI's StaticFiles mounts (`/frames`, `/fonts`, `/output`, and `/static`)

## How It Works

### Storage Fallback Chain

The application uses a tiered storage approach:

1. **Primary**: Cloudflare R2 (CDN-backed cloud storage)
2. **Fallback**: Local filesystem (`backend/public/output/`)

When R2 credentials are missing or upload fails, the system automatically falls back to local storage as implemented in [`storage.py`](../services/storage.py:263-282).

### Static File Mounting

In [`main.py`](../main.py:155-167), the application mounts several static directories:

```python
backend_public = Path(__file__).parent / "public"
app.mount("/frames", StaticFiles(directory=backend_public / "frames"))
app.mount("/fonts", StaticFiles(directory=backend_public / "fonts"))
app.mount("/output", StaticFiles(directory=backend_public / "output"))
app.mount("/static", StaticFiles(directory=backend_public))
```

The `backend/public/` directory contains the backend-owned public assets:
- `backend/public/frames/` - Meme template images
- `backend/public/fonts/` - Font files for text rendering
- `backend/public/meme_data.json` - Template metadata

## Output Directory

### Purpose
Stores generated meme images when R2 storage is unavailable.

### Characteristics
- **Temporary Storage**: Files should be periodically cleaned up
- **Git Ignored**: Generated image files are excluded via `backend/public/.gitignore`
- **Auto-Created**: Directory is created automatically by [`storage.py`](../services/storage.py:266) if it doesn't exist

### File Naming
Generated memes use UUID-based filenames: `{uuid4()}.png`

### Access Pattern
Files are accessible via HTTP at: `/output/{filename}`

Example: `/output/a1b2c3d4-e5f6-7890-abcd-ef1234567890.png`

## Configuration

### Environment Variables

Storage behavior is controlled by these environment variables:

- `R2_ACCESS_KEY_ID` - Cloudflare R2 access key
- `R2_SECRET_ACCESS_KEY` - Cloudflare R2 secret key
- `R2_BUCKET_NAME` - R2 bucket name
- `R2_ENDPOINT_URL` - R2 endpoint URL
- `R2_PUBLIC_URL` - Public CDN URL for R2 assets

When these are not configured, the system uses local storage fallback.

## Maintenance

### Cleanup Recommendations

Generated memes in `output/` should be periodically cleaned to prevent disk space issues:

```bash
# Remove files older than 7 days
find backend/public/output -name "*.png" -mtime +7 -delete
```

Consider implementing automated cleanup via:
- Cron job
- Application startup routine
- Background worker task

### Monitoring

Monitor the `output/` directory for:
- **Disk Usage**: Track total size to prevent disk exhaustion
- **File Count**: High counts indicate R2 issues or cleanup failures
- **Growth Rate**: Rapid growth suggests R2 is down

### Storage Migration

To migrate from local to R2 storage:

1. Configure R2 environment variables
2. Restart the application
3. Optionally upload existing files from `output/` to R2
4. Clean up local files after verification

## Related Files

- [`backend/services/storage.py`](../services/storage.py) - Storage service with R2 and local fallback
- [`backend/services/compositor.py`](../services/compositor.py) - Meme image composition
- [`backend/main.py`](../main.py) - FastAPI app with static file mounts
- [`backend/routers/memes.py`](../routers/memes.py) - Meme generation endpoints

## Security Considerations

1. **Public Access**: Files in `output/` are publicly accessible via HTTP
2. **No Authentication**: Static file serving bypasses authentication
3. **File Validation**: Only PNG files should be stored here
4. **Path Traversal**: FastAPI's StaticFiles prevents directory traversal attacks

## Performance

### Local Storage Performance
- **Pros**: Fast access, no network latency, no API costs
- **Cons**: Not scalable, single point of failure, no CDN benefits

### R2 Storage Performance
- **Pros**: CDN-backed, globally distributed, scalable, durable
- **Cons**: Network latency, API rate limits, requires configuration

## Troubleshooting

### Issue: Files not accessible
**Solution**: Verify the directory exists and FastAPI mount is configured

### Issue: Disk space full
**Solution**: Implement cleanup routine or configure R2 storage

### Issue: R2 upload fails
**Solution**: Check R2 credentials and network connectivity. System will automatically fall back to local storage.

### Issue: Generated memes not appearing
**Solution**: Check logs for storage errors. Verify `output/` directory permissions.

## Future Improvements

1. **Automated Cleanup**: Implement background task to remove old files
2. **Storage Metrics**: Add monitoring for disk usage and file counts
3. **Health Checks**: Add endpoint to verify storage availability
4. **Batch Migration**: Tool to migrate local files to R2
5. **Compression**: Implement image optimization before storage
6. **Retention Policy**: Configurable TTL for generated memes
