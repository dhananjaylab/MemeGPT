"""Add Imgflip template support

Revision ID: 20260426_imgflip
Revises: 20260424_phase1
Create Date: 2026-04-26 16:59:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260426_imgflip"
down_revision: Union[str, None] = "56acdf9f25ae"  # Points to the latest migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add Imgflip-specific fields to meme_templates
    op.add_column("meme_templates", sa.Column("source", sa.String(), nullable=False, server_default="local"))
    op.add_column("meme_templates", sa.Column("imgflip_id", sa.String(), nullable=True))
    op.add_column("meme_templates", sa.Column("box_count", sa.Integer(), nullable=True))
    op.add_column("meme_templates", sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))
    
    # Create indexes for efficient querying
    op.create_index(op.f("ix_meme_templates_source"), "meme_templates", ["source"], unique=False)
    op.create_index(op.f("ix_meme_templates_imgflip_id"), "meme_templates", ["imgflip_id"], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f("ix_meme_templates_imgflip_id"), table_name="meme_templates")
    op.drop_index(op.f("ix_meme_templates_source"), table_name="meme_templates")
    
    # Drop columns
    op.drop_column("meme_templates", "last_synced_at")
    op.drop_column("meme_templates", "box_count")
    op.drop_column("meme_templates", "imgflip_id")
    op.drop_column("meme_templates", "source")

# Made with Bob
