"""add multi_alvo support: tipo_acao, modo alvo, disparos, alvo_membros

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-28 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

modo_alvo_enum = postgresql.ENUM("individual", "agregado", name="modoalvo", create_type=False)
tipo_acao_enum = postgresql.ENUM("simples", "multi_alvo", name="tipo_acao", create_type=False)
status_disparo_enum = postgresql.ENUM(
    "ENVIADO", "ENTREGUE", "FALHA", "ERRO_ENVIO", name="status_disparo", create_type=False
)


def _ensure_postgres_enums() -> None:
    """Cria tipos ENUM no PostgreSQL sem duplicar (create_type=False nas colunas)."""
    bind = op.get_bind()
    sa.Enum("individual", "agregado", name="modoalvo").create(bind, checkfirst=True)
    sa.Enum("simples", "multi_alvo", name="tipo_acao").create(bind, checkfirst=True)
    sa.Enum("ENVIADO", "ENTREGUE", "FALHA", "ERRO_ENVIO", name="status_disparo").create(
        bind, checkfirst=True
    )


def upgrade() -> None:
    """Upgrade schema."""
    _ensure_postgres_enums()

    bind = op.get_bind()
    inspector = inspect(bind)
    alvos_columns = {c["name"] for c in inspector.get_columns("alvos")}
    acoes_columns = {c["name"] for c in inspector.get_columns("acoes")}
    tables = set(inspector.get_table_names())

    if "modo" not in alvos_columns:
        op.add_column(
            "alvos",
            sa.Column(
                "modo",
                modo_alvo_enum,
                nullable=False,
                server_default="individual",
            ),
        )

    if "tipo_acao" not in acoes_columns:
        op.add_column(
            "acoes",
            sa.Column(
                "tipo_acao",
                tipo_acao_enum,
                nullable=False,
                server_default="simples",
            ),
        )

    if "disparos" not in tables:
        op.create_table(
            "disparos",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("acao_id", sa.UUID(), nullable=False),
            sa.Column("alvo_id", sa.UUID(), nullable=False),
            sa.Column(
                "status",
                status_disparo_enum,
                nullable=False,
                server_default="ENVIADO",
            ),
            sa.Column("message_id", sa.String(length=200), nullable=True),
            sa.Column("proximo_passo_dados", sa.JSON(), nullable=True),
            sa.Column("confirmado_em", sa.DateTime(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_disparos_acao_id", "disparos", ["acao_id"])
        op.create_index("ix_disparos_alvo_id", "disparos", ["alvo_id"])

    if "alvo_membros" not in tables:
        op.create_table(
            "alvo_membros",
            sa.Column("agregado_id", sa.UUID(), nullable=False),
            sa.Column("membro_id", sa.UUID(), nullable=False),
            sa.ForeignKeyConstraint(["agregado_id"], ["alvos.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["membro_id"], ["alvos.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("agregado_id", "membro_id"),
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    alvos_columns = {c["name"] for c in inspector.get_columns("alvos")}
    acoes_columns = {c["name"] for c in inspector.get_columns("acoes")}

    if "alvo_membros" in tables:
        op.drop_table("alvo_membros")

    if "disparos" in tables:
        op.drop_index("ix_disparos_alvo_id", table_name="disparos")
        op.drop_index("ix_disparos_acao_id", table_name="disparos")
        op.drop_table("disparos")

    if "tipo_acao" in acoes_columns:
        op.drop_column("acoes", "tipo_acao")

    if "modo" in alvos_columns:
        op.drop_column("alvos", "modo")

    sa.Enum("ENVIADO", "ENTREGUE", "FALHA", "ERRO_ENVIO", name="status_disparo").drop(
        bind, checkfirst=True
    )
    sa.Enum("simples", "multi_alvo", name="tipo_acao").drop(bind, checkfirst=True)
    sa.Enum("individual", "agregado", name="modoalvo").drop(bind, checkfirst=True)
