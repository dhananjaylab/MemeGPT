import os
import sys
import re
from logging.config import fileConfig
from sqlalchemy import pool, create_engine
from sqlalchemy.engine import Connection
from alembic import context

# Add the parent directory to the path so we can import our models
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Load .env file if it exists
from dotenv import load_dotenv
# env.py is at: backend/db/migrations/env.py
# .env is at: backend/.env
# So we need to go up 3 levels: migrations -> db -> backend
env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv(env_file, override=True)

# Get database URL from environment or use default
database_url = os.getenv(
    "DATABASE_URL", 
    "postgresql+psycopg2://user:password@localhost/memegpt"
)

# Convert postgresql:// to postgresql+psycopg2://
database_url = re.sub(r'^postgresql:', 'postgresql+psycopg2:', database_url)

from db.session import Base
from models.models import User, GeneratedMeme, MemeJob, MemeTemplate

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set the database URL directly
config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        as_sql=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with psycopg driver."""
    try:
        # Create a sync engine with psycopg
        connectable = create_engine(database_url, poolclass=pool.NullPool)
        
        with connectable.connect() as connection:
            do_run_migrations(connection)
        
        connectable.dispose()
    except Exception as e:
        print(f"\n⚠️  Could not connect to database: {str(e)}")
        print("\nFalling back to offline migration mode (SQL will be generated but not executed).")
        print("To apply migrations, ensure the database is accessible and run: alembic upgrade head\n")
        run_migrations_offline()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()