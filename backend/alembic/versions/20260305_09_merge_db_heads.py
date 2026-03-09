"""Merge indexing and constraint branches into a single migration head.

Revision ID: 20260305_09
Revises: 20260305_07, 20260305_08
Create Date: 2026-03-05 18:40:00.000000
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "20260305_09"
down_revision: tuple[str, str] = ("20260305_07", "20260305_08")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
