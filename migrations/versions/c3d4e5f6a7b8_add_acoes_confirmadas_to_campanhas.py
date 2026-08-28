"""add acoes_confirmadas to campanhas

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-19 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "campanhas",
        sa.Column("acoes_confirmadas", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.execute("""
        UPDATE campanhas
        SET acoes_confirmadas = (
            SELECT COUNT(*) FROM acoes
            WHERE acoes.campanha_id = campanhas.id AND acoes.status = 'CONCLUIDA'
        )
        """)
    # Índice parcial (PostgreSQL). Em SQLite o dialect pode ignorar ou aceitar WHERE.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("""
            CREATE INDEX idx_acoes_campanha_concluida
            ON acoes(campanha_id) WHERE status = 'CONCLUIDA'
            """)
    else:
        op.create_index("idx_acoes_campanha_concluida", "acoes", ["campanha_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_acoes_campanha_concluida", table_name="acoes")
    op.drop_column("campanhas", "acoes_confirmadas")
