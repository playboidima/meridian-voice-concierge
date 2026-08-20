"""Create FAQ and unanswered question tables."""

from alembic import op
import sqlalchemy as sa

revision = "20260820_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "faqs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question", sa.String(length=500), nullable=False, unique=True),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_faqs_category", "faqs", ["category"])
    op.create_table(
        "unanswered_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("original_question", sa.String(length=1000), nullable=False),
        sa.Column("normalized_question", sa.String(length=1000), nullable=False, unique=True),
        sa.Column("frequency", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="open"),
    )
    op.create_index("ix_unanswered_status", "unanswered_questions", ["status"])


def downgrade() -> None:
    op.drop_table("unanswered_questions")
    op.drop_table("faqs")

