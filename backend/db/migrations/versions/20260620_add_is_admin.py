"""add is_admin flag to users for RBAC on admin endpoints

Phase 1 security remediation: several destructive endpoints
(/api/storage/*, /api/jobs/queue/cleanup, /api/memes/seed-templates)
had no authorization check at all. This migration adds the flag that
services.auth.get_current_admin_user checks.

Revision ID: 20260620_add_is_admin
Revises: 20260526_remove_imgflip
Create Date: 2026-06-20
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "20260620_add_is_admin"
down_revision = "20260526_remove_imgflip"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index(op.f("ix_users_is_admin"), "users", ["is_admin"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_is_admin"), table_name="users")
    op.drop_column("users", "is_admin")
