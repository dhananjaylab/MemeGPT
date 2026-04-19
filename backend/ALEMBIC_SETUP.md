# Alembic Database Migration Setup

This document describes the Alembic database migration setup for MemeGPT v2.

## Overview

Alembic is configured to manage database schema changes for the MemeGPT v2 application. The setup includes:

- **Async SQLAlchemy support** for PostgreSQL with asyncpg driver
- **Automatic migration generation** from SQLAlchemy models
- **Production-ready configuration** with proper error handling
- **Database initialization scripts** for easy deployment

## Database Models

The following models are configured for migration:

### 1. User Model (`users` table)
- **Purpose**: Store user account information and subscription details
- **Key Fields**: id, email, plan, daily_limit, daily_used, api_key
- **Indexes**: email (unique), plan, api_key (unique), created_at

### 2. GeneratedMeme Model (`memes` table)
- **Purpose**: Store generated meme data and metadata
- **Key Fields**: id, user_id, prompt, template_name, meme_text, image_url
- **Indexes**: Multiple composite indexes for efficient querying
- **Relationships**: Foreign key to users table

### 3. MemeJob Model (`meme_jobs` table)
- **Purpose**: Track async meme generation jobs
- **Key Fields**: id, user_id, prompt, status, result_meme_ids
- **Indexes**: status, user_id, created_at combinations
- **Relationships**: Foreign key to users table

### 4. MemeTemplate Model (`meme_templates` table)
- **Purpose**: Store meme template definitions and metadata
- **Key Fields**: id, name, alternative_names, file_path, text_coordinates
- **Indexes**: name (unique)

## Configuration Files

### alembic.ini
- **Database URL**: Configured to use PostgreSQL with asyncpg driver
- **Script Location**: `alembic/` directory
- **Logging**: Configured for development and production use

### alembic/env.py
- **Async Support**: Properly configured for async SQLAlchemy operations
- **Model Import**: Imports all models for autogeneration
- **Target Metadata**: Uses Base.metadata from models
- **Error Handling**: Robust connection and migration error handling

## Migration Files

### Initial Migration (17360e17a097)
- **Creates all tables** with proper constraints and indexes
- **Foreign key relationships** between users, memes, and jobs
- **Composite indexes** for efficient querying
- **Proper data types** including JSON fields for flexible data storage

## Usage Instructions

### 1. Database Connection Setup

Ensure PostgreSQL is running and configure the database URL in your environment:

```bash
# Example database URL
DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/memegpt"
```

### 2. Test Database Connection

Before running migrations, test the database connection:

```bash
cd backend
python init_db.py --test-connection
```

### 3. Initialize Database

Create all tables using Alembic migrations:

```bash
cd backend
python init_db.py
```

### 4. Reset Database (Development Only)

To drop and recreate all tables:

```bash
cd backend
python init_db.py --reset
```

### 5. Validate Setup

Run the validation test suite:

```bash
cd backend
python test_alembic_setup.py
```

## Alembic Commands

### Generate New Migration

When you modify models, generate a new migration:

```bash
cd backend
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations

Apply pending migrations to the database:

```bash
cd backend
alembic upgrade head
```

### Check Migration Status

View current migration status:

```bash
cd backend
alembic current
alembic history --verbose
```

### Rollback Migration

Rollback to a previous migration:

```bash
cd backend
alembic downgrade -1  # Go back one migration
alembic downgrade <revision_id>  # Go to specific revision
```

## Production Deployment

### 1. Environment Variables

Set the following environment variables in production:

```bash
DATABASE_URL="postgresql+asyncpg://user:password@host:5432/database"
ENVIRONMENT="production"
```

### 2. Migration Deployment

Run migrations as part of your deployment process:

```bash
# In your deployment script
cd backend
python init_db.py --test-connection
python init_db.py  # This will run migrations if needed
```

### 3. Backup Strategy

Always backup your database before running migrations in production:

```bash
# Example backup command
pg_dump -h host -U user -d database > backup_$(date +%Y%m%d_%H%M%S).sql
```

## Troubleshooting

### Common Issues

1. **Connection Refused Error**
   - Ensure PostgreSQL is running
   - Check database URL configuration
   - Verify network connectivity

2. **Import Errors in env.py**
   - Check Python path configuration
   - Ensure all models are properly imported
   - Verify relative import paths

3. **Migration Generation Issues**
   - Ensure models are properly registered with Base
   - Check for circular imports
   - Verify SQLAlchemy model definitions

### Debug Mode

Enable debug logging by setting echo=True in the database engine configuration:

```python
# In db/session.py
engine = create_async_engine(
    settings.database_url,
    echo=True,  # Enable SQL logging
    future=True,
)
```

## File Structure

```
backend/
├── alembic/
│   ├── versions/
│   │   └── 17360e17a097_initial_migration_create_all_tables.py
│   ├── env.py
│   └── script.py.mako
├── alembic.ini
├── models/
│   └── models.py
├── db/
│   └── session.py
├── core/
│   └── config.py
├── init_db.py
├── test_alembic_setup.py
└── ALEMBIC_SETUP.md
```

## Best Practices

1. **Always review generated migrations** before applying them
2. **Test migrations on a copy of production data** before deployment
3. **Keep migration files in version control**
4. **Use descriptive migration messages**
5. **Backup database before major schema changes**
6. **Monitor migration performance** on large tables

## Integration with FastAPI

The database session is configured for use with FastAPI dependency injection:

```python
from db.session import get_db

@app.get("/users/")
async def get_users(db: AsyncSession = Depends(get_db)):
    # Use db session here
    pass
```

## Next Steps

After setting up Alembic migrations:

1. **Start the FastAPI backend**: `python main.py`
2. **Start the ARQ worker**: `python worker.py`
3. **Access API documentation**: `http://localhost:8000/docs`
4. **Test meme generation endpoints**
5. **Verify database operations**

For more information, see the main project documentation and the FastAPI backend setup guide.