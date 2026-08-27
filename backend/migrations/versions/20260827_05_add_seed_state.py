"""Preserve existing FAQ catalogs and seed new installations only once."""

from alembic import context, op
import sqlalchemy as sa


revision = "20260827_05"
down_revision = "20260824_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if context.is_offline_mode():
        raise RuntimeError("Seed-state migration requires an online database connection")
    state = op.create_table(
        "seed_state",
        sa.Column("name", sa.String(100), primary_key=True),
        sa.Column("applied", sa.Boolean(), nullable=False),
    )
    op.bulk_insert(state, [{
        "name": "meridian_faq_v1",
        "applied": context.config.attributes["existing_installation"],
    }])


def downgrade() -> None:
    op.drop_table("seed_state")
