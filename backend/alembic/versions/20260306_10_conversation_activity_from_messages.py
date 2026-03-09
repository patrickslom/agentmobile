"""Keep conversation activity timestamp in sync with message turns.

Revision ID: 20260306_10
Revises: 20260305_09
Create Date: 2026-03-06 00:10:00.000000
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260306_10"
down_revision: str | None = "20260305_09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION touch_conversation_updated_at_from_message()
        RETURNS TRIGGER AS $$
        DECLARE
            target_conversation_id UUID;
        BEGIN
            target_conversation_id := COALESCE(NEW.conversation_id, OLD.conversation_id);

            UPDATE conversations
            SET updated_at = now()
            WHERE id = target_conversation_id;

            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_messages_touch_conversation_updated_at
        AFTER INSERT OR UPDATE OR DELETE ON messages
        FOR EACH ROW
        EXECUTE FUNCTION touch_conversation_updated_at_from_message()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_messages_touch_conversation_updated_at ON messages"
    )
    op.execute("DROP FUNCTION IF EXISTS touch_conversation_updated_at_from_message()")
