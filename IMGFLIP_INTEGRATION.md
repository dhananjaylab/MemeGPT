# Imgflip Integration Guide

## Overview

MemeGPT now supports fetching popular meme templates from Imgflip API, providing users with access to 100+ trending templates in addition to the local database templates.

## Features

- ✅ Fetch top 100 popular templates from Imgflip
- ✅ Database caching for 24-hour periods
- ✅ Source filtering (All, Database, Imgflip)
- ✅ Visual source badges on template cards
- ✅ One-click sync button
- ✅ Automatic text coordinate generation
- ✅ Seamless integration with manual editor

## Architecture

```
┌─────────────────┐
│  User Interface │
│ (TemplateSelector)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Backend API    │
│ /api/memes/     │
│  templates      │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌──────────┐
│Database│ │ Imgflip  │
│Templates│ │ Service  │
└────────┘ └─────┬────┘
                 │
                 ▼
          ┌──────────────┐
          │ Imgflip API  │
          │ (External)   │
          └──────────────┘
```

## Setup Instructions

### 1. Environment Configuration

Add Imgflip credentials to your `.env` file (optional - public API works without auth):

```bash
# Imgflip API (optional - for higher rate limits)
IMGFLIP_USERNAME=your_username
IMGFLIP_PASSWORD=your_password
```

### 2. Database Migration

Run the migration to add Imgflip support fields:

```bash
cd backend
alembic upgrade head
```

This adds the following fields to `meme_templates`:
- `source` (String): "local" or "imgflip"
- `imgflip_id` (String): Imgflip template ID
- `box_count` (Integer): Number of text boxes
- `last_synced_at` (DateTime): Last sync timestamp

### 3. Initial Sync

Sync Imgflip templates using the API endpoint:

```bash
curl -X POST http://localhost:8000/api/memes/templates/sync-imgflip
```

Or use the "Sync Imgflip Templates" button in the UI.

## API Endpoints

### Get Templates (with filtering)

```http
GET /api/memes/templates?source={all|local|imgflip}
```

**Query Parameters:**
- `source` (optional): Filter by template source
  - `all` - All templates (default)
  - `local` - Database templates only
  - `imgflip` - Imgflip templates only

**Response:**
```json
[
  {
    "id": 1,
    "name": "Drake Hotline Bling",
    "image_url": "https://i.imgflip.com/30b1gx.jpg",
    "text_field_count": 2,
    "text_coordinates": [[10, 5, 80, 20], [10, 75, 80, 20]],
    "preview_image_url": "https://i.imgflip.com/30b1gx.jpg",
    "font_path": "fonts/impact.ttf",
    "usage_instructions": "Imgflip template: Drake Hotline Bling",
    "source": "imgflip",
    "imgflip_id": "181913649"
  }
]
```

### Sync Imgflip Templates

```http
POST /api/memes/templates/sync-imgflip
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully synced Imgflip templates",
  "stats": {
    "fetched": 100,
    "created": 95,
    "updated": 5,
    "errors": 0
  }
}
```

## Frontend Integration

### Template Selector Component

The `TemplateSelector` component now includes:

1. **Source Filter Tabs**
   - All Templates
   - Database (local templates)
   - Imgflip (external templates)

2. **Source Badges**
   - Blue badge with globe icon for Imgflip templates
   - Purple badge with database icon for local templates

3. **Sync Button**
   - One-click sync of Imgflip templates
   - Shows loading state during sync
   - Toast notifications for success/error

### Usage Example

```tsx
import { TemplateSelector } from './components/TemplateSelector';

function MyComponent() {
  const handleSelectTemplate = (template) => {
    console.log('Selected:', template);
    // Template includes source and imgflip_id fields
  };

  return (
    <TemplateSelector
      onSelectTemplate={handleSelectTemplate}
      selectedTemplateId={selectedId}
    />
  );
}
```

## Text Coordinate Generation

Imgflip templates don't include text coordinates, so they're automatically generated based on `box_count`:

### 1 Text Box
```javascript
[[10, 5, 80, 20]]  // Top center
```

### 2 Text Boxes
```javascript
[
  [10, 5, 80, 20],   // Top
  [10, 75, 80, 20]   // Bottom
]
```

### 3 Text Boxes
```javascript
[
  [10, 5, 80, 15],   // Top
  [10, 42, 80, 15],  // Middle
  [10, 80, 80, 15]   // Bottom
]
```

### 4+ Text Boxes
Evenly distributed vertically with 15% height each.

## Caching Strategy

- **Cache Duration**: 24 hours
- **Storage**: PostgreSQL database
- **Update Strategy**: Upsert (update existing, insert new)
- **Sync Trigger**: Manual via API or automatic check

### Cache Check Logic

```python
async def should_sync(db: AsyncSession) -> bool:
    """Check if sync is needed based on last sync time"""
    last_sync = await get_last_sync_time(db)
    if not last_sync:
        return True  # Never synced
    
    cache_expiry = last_sync + timedelta(hours=24)
    return datetime.utcnow() > cache_expiry
```

## Error Handling

### Imgflip API Failures
- Graceful fallback to database templates only
- Error logged but doesn't break template loading
- User notified via toast message

### Duplicate Templates
- Checked by `imgflip_id` before insertion
- Existing templates updated with latest data
- No duplicate entries created

### Missing Data
- Default values provided for missing fields
- Text coordinates generated automatically
- Font defaults to Impact

## Performance Considerations

1. **Database Indexing**
   - Index on `source` field for fast filtering
   - Unique index on `imgflip_id` for deduplication

2. **API Rate Limiting**
   - Imgflip public API: ~100 requests/hour
   - Cached responses reduce API calls
   - Sync only when cache expires

3. **Image Loading**
   - Imgflip CDN URLs used directly
   - No local image storage required
   - Fast loading from Imgflip's CDN

## Monitoring

### Sync Statistics

Track sync operations:
```json
{
  "fetched": 100,    // Templates fetched from Imgflip
  "created": 95,     // New templates added
  "updated": 5,      // Existing templates updated
  "errors": 0        // Failed template syncs
}
```

### Database Queries

Monitor template queries by source:
```sql
-- Count templates by source
SELECT source, COUNT(*) 
FROM meme_templates 
GROUP BY source;

-- Check last sync time
SELECT MAX(last_synced_at) 
FROM meme_templates 
WHERE source = 'imgflip';
```

## Troubleshooting

### Templates Not Showing

1. Check if sync completed successfully
2. Verify database migration ran
3. Check source filter setting
4. Inspect browser console for errors

### Sync Failures

1. Check Imgflip API status
2. Verify network connectivity
3. Check database connection
4. Review backend logs

### Text Positioning Issues

1. Verify `text_coordinates` are generated
2. Check `box_count` matches template
3. Adjust coordinates in database if needed

## Future Enhancements

- [ ] Automatic background sync (cron job)
- [ ] Template popularity tracking
- [ ] Custom text coordinate editor
- [ ] Imgflip template search by keyword
- [ ] Template preview before selection
- [ ] Favorite templates feature

## Related Files

### Backend
- `backend/services/imgflip.py` - Imgflip service
- `backend/routers/memes.py` - API endpoints
- `backend/models/models.py` - Database models
- `backend/core/config.py` - Configuration
- `backend/db/migrations/versions/20260426_add_imgflip_support.py` - Migration

### Frontend
- `frontend/src/components/TemplateSelector.tsx` - Template selector UI
- `frontend/src/lib/types.ts` - TypeScript types
- `frontend/src/components/MemeGenerator.tsx` - Meme generator

## Support

For issues or questions:
1. Check this documentation
2. Review API_DOCUMENTATION.md
3. Check backend logs
4. Open GitHub issue

---

**Last Updated**: 2026-04-26
**Version**: 1.0.0