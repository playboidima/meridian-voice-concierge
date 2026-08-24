"""Add pgvector embeddings to FAQ records."""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import VECTOR


revision = "20260821_02"
down_revision = "20260820_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column("faqs", sa.Column("embedding", VECTOR(384), nullable=True))
    op.create_index(
        "ix_faqs_embedding_hnsw",
        "faqs",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_faqs_embedding_hnsw", table_name="faqs")
    op.drop_column("faqs", "embedding")
    op.execute("DROP EXTENSION IF EXISTS vector")
