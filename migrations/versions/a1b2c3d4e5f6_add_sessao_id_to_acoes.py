"""add sessao_id to acoes

Revision ID: a1b2c3d4e5f6
Revises: c27ae51dbfb1
Create Date: 2026-08-19 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "907c99c7ce8c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("acoes", sa.Column("sessao_id", sa.String(length=36), nullable=True))
    op.add_column("acoes", sa.Column("ativista_preenchido_em", sa.DateTime(), nullable=True))
    op.create_index(op.f("ix_acoes_sessao_id"), "acoes", ["sessao_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_acoes_sessao_id"), table_name="acoes")
    op.drop_column("acoes", "ativista_preenchido_em")
    op.drop_column("acoes", "sessao_id")
