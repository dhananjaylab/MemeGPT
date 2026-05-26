"""remove imgflip template support

Revision ID: 20260526_remove_imgflip
Revises: 20260517_hash_keys
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa


revision = "20260526_remove_imgflip"
down_revision = "20260517_hash_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM meme_templates WHERE source = 'imgflip'")
    op.drop_index(op.f("ix_meme_templates_imgflip_id"), table_name="meme_templates")
    op.drop_column("meme_templates", "last_synced_at")
    op.drop_column("meme_templates", "box_count")
    op.drop_column("meme_templates", "imgflip_id")


def downgrade() -> None:
    op.add_column("meme_templates", sa.Column("imgflip_id", sa.String(), nullable=True))
    op.add_column("meme_templates", sa.Column("box_count", sa.Integer(), nullable=True))
    op.add_column("meme_templates", sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_meme_templates_imgflip_id"), "meme_templates", ["imgflip_id"], unique=True)
