"""add ligacoes table and campanhas.telefone_origem

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-10-08 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "b8c9d0e1f2a3"
down_revision: str | Sequence[str] | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ETAPAS = (
    "INICIANDO",
    "CHAMANDO_ATIVISTA",
    "CHAMANDO_ALVO",
    "EM_ANDAMENTO",
    "CONCLUIDA",
    "FALHA",
)
ORIGENS = ("ativista", "alvo")

status_ligacao_enum = postgresql.ENUM(*ETAPAS, name="status_ligacao", create_type=False)
origem_falha_enum = postgresql.ENUM(*ORIGENS, name="origem_falha_ligacao", create_type=False)


def _ensure_postgres_enums() -> None:
    """Cria tipos ENUM no PostgreSQL sem duplicar (create_type=False nas colunas)."""
    bind = op.get_bind()
    sa.Enum(*ETAPAS, name="status_ligacao").create(bind, checkfirst=True)
    sa.Enum(*ORIGENS, name="origem_falha_ligacao").create(bind, checkfirst=True)


def upgrade() -> None:
    """Upgrade schema."""
    _ensure_postgres_enums()

    bind = op.get_bind()
    inspector = inspect(bind)
    campanhas_columns = {c["name"] for c in inspector.get_columns("campanhas")}
    tables = set(inspector.get_table_names())

    if "telefone_origem" not in campanhas_columns:
        op.add_column("campanhas", sa.Column("telefone_origem", sa.String(length=20), nullable=True))
        op.create_unique_constraint(
            "uq_campanhas_telefone_origem", "campanhas", ["telefone_origem"]
        )

    if "ligacoes" not in tables:
        op.create_table(
            "ligacoes",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("acao_id", sa.UUID(), nullable=False),
            sa.Column("disparo_id", sa.UUID(), nullable=False),
            sa.Column("alvo_id", sa.UUID(), nullable=False),
            sa.Column("telefone_ativista", sa.String(length=20), nullable=False),
            sa.Column("telefone_alvo", sa.String(length=20), nullable=False),
            sa.Column(
                "etapa", status_ligacao_enum, nullable=False, server_default="INICIANDO"
            ),
            sa.Column("origem_falha", origem_falha_enum, nullable=True),
            sa.Column("motivo_falha", sa.String(length=20), nullable=True),
            sa.Column("provedor", sa.String(length=20), nullable=False),
            sa.Column("provedor_call_id", sa.String(length=64), nullable=True),
            sa.Column("provedor_call_id_alvo", sa.String(length=64), nullable=True),
            sa.Column("selecao", sa.String(length=20), nullable=False),
            sa.Column("duracao_seg", sa.Integer(), nullable=True),
            sa.Column("iniciada_em", sa.DateTime(), nullable=True),
            sa.Column("alvo_atendeu_em", sa.DateTime(), nullable=True),
            sa.Column("finalizada_em", sa.DateTime(), nullable=True),
            sa.Column("eventos", sa.JSON(), nullable=False),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("disparo_id", name="uq_ligacoes_disparo_id"),
        )
        op.create_index("ix_ligacoes_acao_id", "ligacoes", ["acao_id"])
        op.create_index("ix_ligacoes_alvo_id", "ligacoes", ["alvo_id"])
        op.create_index("ix_ligacoes_provedor_call_id", "ligacoes", ["provedor_call_id"])


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    campanhas_columns = {c["name"] for c in inspector.get_columns("campanhas")}

    if "ligacoes" in tables:
        op.drop_index("ix_ligacoes_provedor_call_id", table_name="ligacoes")
        op.drop_index("ix_ligacoes_alvo_id", table_name="ligacoes")
        op.drop_index("ix_ligacoes_acao_id", table_name="ligacoes")
        op.drop_table("ligacoes")

    if "telefone_origem" in campanhas_columns:
        op.drop_constraint("uq_campanhas_telefone_origem", "campanhas", type_="unique")
        op.drop_column("campanhas", "telefone_origem")

    sa.Enum(*ORIGENS, name="origem_falha_ligacao").drop(bind, checkfirst=True)
    sa.Enum(*ETAPAS, name="status_ligacao").drop(bind, checkfirst=True)
