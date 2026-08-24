"""Add the fixed Meridian voice catalog."""

import sqlalchemy as sa
from alembic import op


revision = "20260824_04"
down_revision = "20260821_03"
branch_labels = None
depends_on = None


voice_configs = sa.table(
    "voice_configs",
    sa.column("name", sa.String),
    sa.column("provider_voice_id", sa.String),
    sa.column("description", sa.Text),
    sa.column("preview_path", sa.String),
    sa.column("is_active", sa.Boolean),
)


def upgrade() -> None:
    op.create_table(
        "voice_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False, unique=True),
        sa.Column(
            "provider_voice_id", sa.String(length=100), nullable=False, unique=True
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("preview_path", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "uq_voice_configs_one_active",
        "voice_configs",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )
    op.bulk_insert(
        voice_configs,
        [
            {
                "name": "James",
                "provider_voice_id": "63ff761f-c1e8-414b-b969-d1833d1c870c",
                "description": "Mature, warm British male; professional and refined.",
                "preview_path": "voice-previews/james.mp3",
                "is_active": True,
            },
            {
                "name": "Sofia",
                "provider_voice_id": "79a125e8-cd45-4c13-8a67-188112f4dd22",
                "description": "Friendly, elegant female with a light European accent.",
                "preview_path": "voice-previews/sofia.mp3",
                "is_active": False,
            },
            {
                "name": "Marcus",
                "provider_voice_id": "a167e0f3-df7e-4d52-a9c3-f949145efdab",
                "description": "Confident, energetic, modern American male.",
                "preview_path": "voice-previews/marcus.mp3",
                "is_active": False,
            },
            {
                "name": "Elena",
                "provider_voice_id": "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
                "description": "Calm, reassuring, clear American female.",
                "preview_path": "voice-previews/elena.mp3",
                "is_active": False,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("uq_voice_configs_one_active", table_name="voice_configs")
    op.drop_table("voice_configs")
