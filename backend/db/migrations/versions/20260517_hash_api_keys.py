"""hash existing plaintext api keys and add api_key_prefix column

Revision ID: 20260517_hash_keys
Revises: 20260517_trending
Create Date: 2026-05-17
"""
import hashlib
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers
revision = "20260517_hash_keys"
down_revision = "20260517_trending"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add api_key_prefix column
    op.add_column(
        "users",
        sa.Column("api_key_prefix", sa.String(), nullable=True),
    )

    # 2. Migrate existing plaintext API keys to SHA-256 hashes + prefixes
    connection = op.get_bind()
    
    # Select users with an existing api_key
    query = text("SELECT id, api_key FROM users WHERE api_key IS NOT NULL")
    results = connection.execute(query).fetchall()

    for row in results:
        user_id = row[0]
        current_key = row[1]

        if current_key and current_key.startswith("mgpt_"):
            # It's a plaintext key
            raw = current_key[len("mgpt_"):]
            key_prefix = f"mgpt_{raw[:8]}…"
            key_hash = hashlib.sha256(current_key.encode("utf-8")).hexdigest()

            update_query = text(
                "UPDATE users SET api_key = :key_hash, api_key_prefix = :key_prefix WHERE id = :user_id"
            )
            connection.execute(
                update_query,
                {"key_hash": key_hash, "key_prefix": key_prefix, "user_id": user_id}
            )
        elif current_key and not current_key.startswith("mgpt_"):
            # It's already a hash (64 hex chars), assign a generic masked prefix
            update_query = text(
                "UPDATE users SET api_key_prefix = :key_prefix WHERE id = :user_id"
            )
            connection.execute(
                update_query,
                {"key_prefix": "mgpt_••••••••••", "user_id": user_id}
            )


def downgrade() -> None:
    op.drop_column("users", "api_key_prefix")
