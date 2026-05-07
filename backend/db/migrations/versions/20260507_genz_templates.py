"""Add Gen-Z templates and template metadata fields

Revision ID: 20260507_genz_templates
Revises: 20260426_imgflip
Create Date: 2026-05-07 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20260507_genz_templates"
down_revision: Union[str, None] = "20260426_imgflip"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. New columns on meme_templates ─────────────────────────────────────
    op.add_column(
        "meme_templates",
        sa.Column("fallback_url", sa.String(), nullable=True),
    )
    op.add_column(
        "meme_templates",
        sa.Column("gen_z_ready", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "meme_templates",
        sa.Column("vibe_tags", sa.JSON(), nullable=True),
    )

    # ── 2. Index for quick filtering by gen_z_ready ───────────────────────────
    op.create_index(
        "ix_meme_templates_gen_z_ready",
        "meme_templates",
        ["gen_z_ready"],
        unique=False,
    )

    # ── 3. Back-fill existing templates as gen_z_ready ────────────────────────
    op.execute(
        "UPDATE meme_templates SET gen_z_ready = true WHERE id IN (0,1,2,3,4,5,6,7,8,9,10)"
    )


def downgrade() -> None:
    op.drop_index("ix_meme_templates_gen_z_ready", table_name="meme_templates")
    op.drop_column("meme_templates", "vibe_tags")
    op.drop_column("meme_templates", "gen_z_ready")
    op.drop_column("meme_templates", "fallback_url")
