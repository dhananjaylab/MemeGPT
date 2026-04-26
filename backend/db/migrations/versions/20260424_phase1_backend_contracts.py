"""Phase 1 backend contracts and metadata fields

Revision ID: 20260424_phase1
Revises: 17360e17a097
Create Date: 2026-04-24 22:45:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260424_phase1"
down_revision: Union[str, None] = "17360e17a097"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # meme_jobs metadata for provider + generation mode
    op.add_column("meme_jobs", sa.Column("ai_provider", sa.String(), nullable=False, server_default="openai"))
    op.add_column("meme_jobs", sa.Column("generation_mode", sa.String(), nullable=False, server_default="auto"))
    op.add_column("meme_jobs", sa.Column("manual_template_id", sa.Integer(), nullable=True))
    op.add_column("meme_jobs", sa.Column("manual_captions", sa.JSON(), nullable=True))
    op.create_index(op.f("ix_meme_jobs_ai_provider"), "meme_jobs", ["ai_provider"], unique=False)
    op.create_index(op.f("ix_meme_jobs_generation_mode"), "meme_jobs", ["generation_mode"], unique=False)

    # canonical template fields used by frontend contract
    op.add_column("meme_templates", sa.Column("text_coordinates", sa.JSON(), nullable=True))
    op.add_column("meme_templates", sa.Column("preview_image_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("meme_templates", "preview_image_url")
    op.drop_column("meme_templates", "text_coordinates")

    op.drop_index(op.f("ix_meme_jobs_generation_mode"), table_name="meme_jobs")
    op.drop_index(op.f("ix_meme_jobs_ai_provider"), table_name="meme_jobs")
    op.drop_column("meme_jobs", "manual_captions")
    op.drop_column("meme_jobs", "manual_template_id")
    op.drop_column("meme_jobs", "generation_mode")
    op.drop_column("meme_jobs", "ai_provider")
