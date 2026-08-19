"""replace ativista_preenchido_em with ativista_preenchido bool

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-19 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("acoes", "ativista_preenchido_em")
    op.add_column("acoes", sa.Column("ativista_preenchido", sa.Boolean(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("acoes", "ativista_preenchido")
    op.add_column("acoes", sa.Column("ativista_preenchido_em", sa.DateTime(), nullable=True))
