# Migration Fix Guide

## Issue
The migration had multiple heads because both `56acdf9f25ae` and `20260426_imgflip` were pointing to `20260424_phase1` as their parent.

## Solution
Updated `20260426_add_imgflip_support.py` to point to `56acdf9f25ae` as its parent, creating a linear migration chain:

```
17360e17a097 (initial)
    ↓
20260424_phase1
    ↓
56acdf9f25ae (add_missing_columns)
    ↓
20260426_imgflip (add_imgflip_support) ← NEW
```

## How to Apply Migration

### Option 1: Run the migration
```bash
cd backend
alembic upgrade head
```

### Option 2: If database connection issues persist
```bash
# Check current migration status
alembic current

# Show pending migrations
alembic history

# Upgrade to specific revision
alembic upgrade 20260426_imgflip
```

### Option 3: Manual SQL execution
If you need to apply the migration manually:

```sql
-- Add Imgflip-specific fields to meme_templates
ALTER TABLE meme_templates 
ADD COLUMN source VARCHAR NOT NULL DEFAULT 'local',
ADD COLUMN imgflip_id VARCHAR,
ADD COLUMN box_count INTEGER,
ADD COLUMN last_synced_at TIMESTAMP WITH TIME ZONE;

-- Create indexes
CREATE INDEX ix_meme_templates_source ON meme_templates(source);
CREATE UNIQUE INDEX ix_meme_templates_imgflip_id ON meme_templates(imgflip_id);

-- Update alembic version table
INSERT INTO alembic_version (version_num) VALUES ('20260426_imgflip');
```

## Verification

After migration, verify the changes:

```sql
-- Check table structure
\d meme_templates

-- Verify indexes
\di meme_templates*

-- Check migration version
SELECT * FROM alembic_version;
```

Expected output should show:
- `source` column (VARCHAR, NOT NULL, DEFAULT 'local')
- `imgflip_id` column (VARCHAR, nullable)
- `box_count` column (INTEGER, nullable)
- `last_synced_at` column (TIMESTAMP WITH TIME ZONE, nullable)
- Two new indexes on `source` and `imgflip_id`

## Rollback (if needed)

To rollback this migration:

```bash
alembic downgrade 56acdf9f25ae
```

Or manually:

```sql
-- Drop indexes
DROP INDEX IF EXISTS ix_meme_templates_imgflip_id;
DROP INDEX IF EXISTS ix_meme_templates_source;

-- Drop columns
ALTER TABLE meme_templates 
DROP COLUMN IF EXISTS last_synced_at,
DROP COLUMN IF EXISTS box_count,
DROP COLUMN IF EXISTS imgflip_id,
DROP COLUMN IF EXISTS source;

-- Update version
DELETE FROM alembic_version WHERE version_num = '20260426_imgflip';
```

## Next Steps

After successful migration:

1. Sync Imgflip templates:
```bash
curl -X POST http://localhost:8000/api/memes/templates/sync-imgflip
```

2. Verify templates loaded:
```sql
SELECT source, COUNT(*) FROM meme_templates GROUP BY source;
```

Expected output:
```
 source  | count
---------+-------
 local   |    50
 imgflip |   100
```

## Troubleshooting

### "Multiple head revisions" error
- Fixed by updating `down_revision` in `20260426_add_imgflip_support.py`
- Ensure you have the latest version of the file

### Database connection issues
- Check PostgreSQL is running
- Verify DATABASE_URL in `.env`
- Try manual SQL execution (Option 3 above)

### Migration already applied
```bash
# Check if migration is already applied
alembic current

# If showing 20260426_imgflip, you're good!
# If not, run: alembic upgrade head