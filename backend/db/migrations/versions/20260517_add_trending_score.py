"""add trending_score column to memes

Revision ID: 20260517_trending
Revises: 20260507_genz_templates
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "20260517_trending"
down_revision = "20260507_genz_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add the trending_score column with a default of 0.0
    op.add_column(
        "memes",
        sa.Column("trending_score", sa.Float(), nullable=False, server_default="0"),
    )
    # Composite index for the trending query: WHERE is_public ORDER BY trending_score
    op.create_index(
        "ix_memes_public_trending",
        "memes",
        ["is_public", "trending_score"],
    )
    # Back-fill existing rows: trending_score = share_count * 0.7 + like_count * 0.3
    op.execute(
        "UPDATE memes SET trending_score = "
        "COALESCE(share_count, 0) * 0.7 + COALESCE(like_count, 0) * 0.3"
    )


def downgrade() -> None:
    op.drop_index("ix_memes_public_trending", table_name="memes")
    op.drop_column("memes", "trending_score")
