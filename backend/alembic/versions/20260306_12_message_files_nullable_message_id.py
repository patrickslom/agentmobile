"""Allow conversation-level file attachments with nullable message linkage.

Revision ID: 20260306_12
Revises: 20260306_11
Create Date: 2026-03-06 11:35:00.000000
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260306_12"
down_revision: str | None = "20260306_11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "message_files",
        "message_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM message_files
        WHERE message_id IS NULL
        """
    )
    op.alter_column(
        "message_files",
        "message_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
        existing_nullable=True,
    )
