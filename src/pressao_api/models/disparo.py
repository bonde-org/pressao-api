import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID

from pressao_api.core.database import Base


class Disparo(Base):
    """Envio individual vinculado a uma ação multi-alvo."""

    __tablename__ = "disparos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    acao_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    alvo_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    status = Column(
        Enum("ENVIADO", "ENTREGUE", "FALHA", "ERRO_ENVIO", name="status_disparo"),
        default="ENVIADO",
        nullable=False,
    )
    message_id = Column(String(200), nullable=True)
    proximo_passo_dados = Column(JSON, nullable=True)
    confirmado_em = Column(DateTime, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Disparo {self.id} acao={self.acao_id} status={self.status}>"
