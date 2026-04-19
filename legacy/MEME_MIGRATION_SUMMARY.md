# Meme Template Migration Summary

## Task 1.2.3: Migrate existing meme_data.json to new database format

### ✅ Migration Status: READY FOR EXECUTION

The migration script has been successfully created and tested. All validation tests pass.

## Migration Overview

This migration transforms the existing `meme_data.json` file from the v1 format into the new v2 database schema using the `MemeTemplate` model.

### Source Data Analysis

**File**: `meme_data.json` (project root)
**Templates Found**: 11 meme templates
**Validation Status**: ✅ All templates pass validation

### Template Inventory

| ID | Template Name | Text Fields | File Path | Alternative Names |
|----|---------------|-------------|-----------|-------------------|
| 0 | Drake Hotline Bling Meme | 2 | Drake-Hotline-Bling.jpg | drakeposting, drakepost, drake like dislike |
| 1 | Distracted Boyfriend | 3 | Distracted-Boyfriend.jpg | guy checking out another girl, jealous girlfriend, wandering eyes |
| 2 | Left Exit 12 Off Ramp | 3 | Left-Exit-12-Off-Ramp.jpg | car drifts off highway, car drift meme, freeway exit |
| 3 | UNO Draw 25 Cards | 2 | UNO-Draw-25-Cards.jpg | do something you don't like or draw 25 cards, uno or draw 25, draw 25 meme |
| 4 | One Does Not Simply | 2 | One-Does-Not-Simply.jpg | one does not simply walk into Mordor, lord of the rings Boromir, one does not simply blank |
| 5 | Expanding Brain | 4 | Expanding-Brain.jpg | levels of intelligence, expanding mind, 500 iq |
| 6 | Hide the Pain Harold | 2 | Hide-the-Pain-Harold.jpg | sad life harold, maurice, herold |
| 7 | Success Kid | 2 | Success-Kid.jpg | Motivation Baby, Motivation Kid, Success Baby |
| 8 | But That's None Of My Business | 2 | But-Thats-None-Of-My-Business.jpg | kermit drinking lipton iced tea, kermit lipton, kermit drinking tea |
| 9 | Disaster Girl | 2 | Disaster-Girl.jpg | evil girl fire, girl house on fire, arson girl |
| 10 | Roll Safe Think About It | 2 | Roll-Safe-Think-About-It.jpg | guy tapping head, whimsical guy, terrible genius advice |

## Migration Process

### 1. Data Validation ✅
- **JSON Structure**: Valid list of 11 template objects
- **Required Fields**: All templates contain required fields
- **Data Types**: All field types match expected schema
- **Coordinates**: Text coordinate arrays match field counts
- **Examples**: Example outputs match text field counts

### 2. Schema Mapping ✅
The migration maps v1 JSON fields to v2 database schema:

```python
# V1 JSON → V2 Database Schema
{
    "id": template.id,                           # Integer primary key
    "name": template.name,                       # String, unique
    "alternative_names": template.alternative_names,  # JSON array
    "file_path": template.file_path,             # String
    "font_path": template.font_path,             # String
    "text_color": template.text_color,           # String
    "text_stroke": template.text_stroke,         # Boolean
    "usage_instructions": template.usage_instructions,  # Text
    "number_of_text_fields": template.number_of_text_fields,  # Integer
    "text_coordinates_xy_wh": template.text_coordinates_xy_wh,  # JSON array
    "example_output": template.example_output    # JSON array
}
```

### 3. Data Integrity Checks ✅
- **Coordinate Validation**: All coordinate arrays are [x, y, width, height] format
- **Field Count Consistency**: Text coordinates and examples match `number_of_text_fields`
- **JSON Serialization**: All data is JSON-serializable for database storage
- **Unique Names**: All template names are unique

## Migration Scripts

### Primary Migration Script
**File**: `backend/migrate_meme_templates.py`
**Features**:
- Loads and validates `meme_data.json`
- Connects to PostgreSQL database
- Performs atomic migration with rollback on failure
- Includes backup functionality
- Supports dry-run mode for testing
- Comprehensive error handling and validation

**Usage**:
```bash
# Test migration without changes
python migrate_meme_templates.py --dry-run

# Create backup and migrate
python migrate_meme_templates.py --backup

# Standard migration
python migrate_meme_templates.py
```

### Validation Test Script
**File**: `backend/test_meme_data_simple.py`
**Purpose**: Validates migration logic without database dependencies
**Status**: ✅ All tests pass (4/4)

## Database Requirements

### Prerequisites
1. **PostgreSQL Database**: Running and accessible
2. **Alembic Migrations**: Applied (`alembic upgrade head`)
3. **Database Tables**: `meme_templates` table must exist
4. **Connection**: Valid `DATABASE_URL` in environment

### Target Schema
```sql
CREATE TABLE meme_templates (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    alternative_names JSON NOT NULL,
    file_path VARCHAR NOT NULL,
    font_path VARCHAR NOT NULL,
    text_color VARCHAR NOT NULL,
    text_stroke BOOLEAN DEFAULT FALSE,
    usage_instructions TEXT NOT NULL,
    number_of_text_fields INTEGER NOT NULL,
    text_coordinates_xy_wh JSON NOT NULL,
    example_output JSON NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Migration Safety Features

### Data Preservation
- **Backup Creation**: Optional backup of existing templates before migration
- **Atomic Operations**: All-or-nothing migration with rollback on failure
- **Validation**: Comprehensive pre-migration validation
- **Verification**: Post-migration integrity checks

### Error Handling
- **Connection Testing**: Validates database connectivity before migration
- **Schema Validation**: Ensures target tables exist
- **Data Validation**: Validates all template data before insertion
- **Rollback**: Automatic rollback on any failure

### Dry Run Support
- **Preview Mode**: Shows what would be migrated without making changes
- **Validation Only**: Tests all logic without database modifications
- **Safe Testing**: Allows validation of migration logic

## Expected Results

After successful migration:

1. **Database State**:
   - 11 meme templates inserted into `meme_templates` table
   - All template metadata preserved
   - Proper timestamps set for `created_at` and `updated_at`

2. **Data Integrity**:
   - All original JSON data preserved in database format
   - Text coordinates and examples properly stored as JSON
   - Alternative names searchable via JSON queries

3. **Functionality**:
   - Templates available for meme generation
   - Searchable by name and alternative names
   - Coordinate data ready for image processing

## Verification Steps

After migration, verify success by:

1. **Count Check**: `SELECT COUNT(*) FROM meme_templates;` should return 11
2. **Data Sampling**: Verify a few templates have correct data
3. **JSON Fields**: Ensure JSON arrays are properly stored
4. **Unique Constraints**: Verify name uniqueness is enforced

## Next Steps

1. **Database Setup**: Ensure PostgreSQL is running with proper migrations
2. **Environment Config**: Set correct `DATABASE_URL` in backend/.env
3. **Run Migration**: Execute `python migrate_meme_templates.py`
4. **Verify Results**: Check database contains all 11 templates
5. **Test Integration**: Verify meme generation works with migrated templates

## Files Created

- `backend/migrate_meme_templates.py` - Main migration script
- `backend/test_meme_data_simple.py` - Validation test script
- `backend/MEME_MIGRATION_SUMMARY.md` - This summary document

## Migration Command

When ready to execute:

```bash
cd backend
python migrate_meme_templates.py --backup
```

This will create a backup and perform the migration safely.