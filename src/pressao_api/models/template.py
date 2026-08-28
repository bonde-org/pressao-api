import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from pressao_api.core.database import Base


class Template(Base):
    """Modelo de Template de mensagem de uma campanha."""

    __tablename__ = "templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    campanha_id = Column(
        UUID(as_uuid=True), ForeignKey("campanhas.id", ondelete="CASCADE"), nullable=False
    )
    canal = Column(String(20), nullable=False)
    titulo = Column(String(255), nullable=False)
    conteudo = Column(Text, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)

    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Template {self.titulo} ({self.canal})>"
