"""Allow FAQ questions as long as unanswered questions without truncation."""

from alembic import context, op
import sqlalchemy as sa


revision = "20260827_06"
down_revision = "20260827_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("faqs", "question", existing_type=sa.String(500),
                    type_=sa.String(1000), existing_nullable=False)


def downgrade() -> None:
    if context.is_offline_mode():
        raise RuntimeError("Question-length downgrade requires an online database connection")
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM faqs WHERE char_length(question) > 500)")):
        raise RuntimeError("Cannot downgrade: FAQ questions longer than 500 characters exist. Shorten them explicitly first.")
    op.alter_column("faqs", "question", existing_type=sa.String(1000),
                    type_=sa.String(500), existing_nullable=False)
