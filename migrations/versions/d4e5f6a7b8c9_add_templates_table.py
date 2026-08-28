"""add templates table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-24 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "templates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("campanha_id", sa.UUID(), nullable=False),
        sa.Column("canal", sa.String(length=20), nullable=False),
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("conteudo", sa.Text(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["campanha_id"], ["campanhas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_templates_campanha_canal", "templates", ["campanha_id", "canal"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_templates_campanha_canal", table_name="templates")
    op.drop_table("templates")
