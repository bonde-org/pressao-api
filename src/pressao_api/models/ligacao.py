import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Enum, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from pressao_api.core.database import Base

ETAPAS_LIGACAO = (
    "INICIANDO",
    "CHAMANDO_ATIVISTA",
    "CHAMANDO_ALVO",
    "EM_ANDAMENTO",
    "CONCLUIDA",
    "FALHA",
)
ETAPAS_TERMINAIS = ("CONCLUIDA", "FALHA")
ORIGENS_FALHA = ("ativista", "alvo")


class Ligacao(Base):
    """Status de uma tentativa de ligação (1:1 com o disparo) de uma ação de telefone."""

    __tablename__ = "ligacoes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    acao_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    disparo_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    alvo_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    telefone_ativista = Column(String(20), nullable=False)
    telefone_alvo = Column(String(20), nullable=False)

    etapa = Column(
        Enum(*ETAPAS_LIGACAO, name="status_ligacao"),
        default="INICIANDO",
        nullable=False,
    )
    origem_falha = Column(Enum(*ORIGENS_FALHA, name="origem_falha_ligacao"), nullable=True)
    motivo_falha = Column(String(20), nullable=True)

    provedor = Column(String(20), nullable=False)
    provedor_call_id = Column(String(64), nullable=True, index=True)
    provedor_call_id_alvo = Column(String(64), nullable=True)
    selecao = Column(String(20), nullable=False)

    duracao_seg = Column(Integer, nullable=True)
    iniciada_em = Column(DateTime, nullable=True)
    alvo_atendeu_em = Column(DateTime, nullable=True)
    finalizada_em = Column(DateTime, nullable=True)

    eventos = Column(JSON, nullable=False, default=list)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Ligacao {self.id} acao={self.acao_id} etapa={self.etapa}>"
