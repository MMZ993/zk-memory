"""add_note_sync_state_columns

Revision ID: 8b3d2a1f4e90
Revises: d584390723bb
Create Date: 2026-03-31 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8b3d2a1f4e90"
down_revision: Union[str, Sequence[str], None] = "d584390723bb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "notes",
        sa.Column(
            "sync_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "notes",
        sa.Column("sync_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("notes", sa.Column("sync_last_error", sa.Text(), nullable=True))
    op.add_column(
        "notes", sa.Column("sync_last_attempt_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "notes", sa.Column("sync_last_success_at", sa.DateTime(), nullable=True)
    )
    op.execute("UPDATE notes SET sync_status = 'synced' WHERE synced IS TRUE")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("notes", "sync_last_success_at")
    op.drop_column("notes", "sync_last_attempt_at")
    op.drop_column("notes", "sync_last_error")
    op.drop_column("notes", "sync_attempts")
    op.drop_column("notes", "sync_status")
