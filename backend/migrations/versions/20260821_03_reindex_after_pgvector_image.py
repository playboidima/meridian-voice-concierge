"""Rebuild text indexes after moving PostgreSQL from Alpine to Debian."""

from alembic import op


revision = "20260821_03"
down_revision = "20260821_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM faqs
        WHERE id IN (
            SELECT id
            FROM (
                SELECT
                    id,
                    row_number() OVER (PARTITION BY question ORDER BY id DESC) AS duplicate_number
                FROM faqs
            ) ranked_faqs
            WHERE duplicate_number > 1
        )
        """
    )
    op.execute("REINDEX TABLE faqs")
    op.execute("REINDEX TABLE unanswered_questions")


def downgrade() -> None:
    pass
