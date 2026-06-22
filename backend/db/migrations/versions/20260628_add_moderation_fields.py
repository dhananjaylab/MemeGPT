"""add moderation_status and moderation_reason to memes

Phase 2 remediation: previously every generated meme was marked
is_public=True the instant generation succeeded, with no review step.
This adds the columns the new moderation pipeline (services/moderation.py)
writes to. Existing rows back-fill to moderation_status='approved' since
they were already public under the old behavior — we're not retroactively
hiding content that was already live, only changing the gate going forward.

Revision ID: 20260628_add_moderation
Revises: 20260620_add_is_admin
Create Date: 2026-06-28
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "20260628_add_moderation"
down_revision = "20260620_add_is_admin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "memes",
        sa.Column("moderation_status", sa.String(), nullable=False, server_default="pending"),
    )
    op.add_column(
        "memes",
        sa.Column("moderation_reason", sa.String(), nullable=True),
    )
    op.create_index(
        op.f("ix_memes_moderation_status"), "memes", ["moderation_status"], unique=False
    )

    # Back-fill: existing public memes were implicitly "approved" under the
    # old no-review behavior. Don't retroactively flag/hide already-live
    # content; only new generations go through the new gate.
    op.execute(
        "UPDATE memes SET moderation_status = 'approved' WHERE is_public = true"
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_memes_moderation_status"), table_name="memes")
    op.drop_column("memes", "moderation_reason")
    op.drop_column("memes", "moderation_status")
