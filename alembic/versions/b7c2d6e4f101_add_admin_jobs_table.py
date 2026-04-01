"""add_admin_jobs_table

Revision ID: b7c2d6e4f101
Revises: 8b3d2a1f4e90
Create Date: 2026-04-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7c2d6e4f101"
down_revision: Union[str, Sequence[str], None] = "8b3d2a1f4e90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "admin_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="queued",
        ),
        sa.Column(
            "total_items",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "processed_items",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "failed_items",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "pending_items",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_jobs_job_type_created_at",
        "admin_jobs",
        ["job_type", "created_at"],
        unique=False,
    )
    op.create_index(
        "uq_admin_jobs_active_job_type",
        "admin_jobs",
        ["job_type"],
        unique=True,
        sqlite_where=sa.text("status IN ('queued', 'in_progress')"),
        postgresql_where=sa.text("status IN ('queued', 'in_progress')"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_admin_jobs_active_job_type", table_name="admin_jobs")
    op.drop_index("ix_admin_jobs_job_type_created_at", table_name="admin_jobs")
    op.drop_table("admin_jobs")
