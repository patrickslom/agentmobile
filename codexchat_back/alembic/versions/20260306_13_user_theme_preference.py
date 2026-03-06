"""Add per-user theme preference.

Revision ID: 20260306_13
Revises: 20260306_12
Create Date: 2026-03-06 06:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260306_13"
down_revision: str | None = "20260306_12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("theme_preference", sa.String(length=16), nullable=True))
    op.create_check_constraint(
        "ck_users_theme_preference",
        "users",
        "theme_preference IS NULL OR theme_preference IN ('light', 'dark')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_theme_preference", "users", type_="check")
    op.drop_column("users", "theme_preference")
