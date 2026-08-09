from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from pressao_api.core.database import Base
import enum

class TipoContato(str, enum.Enum):
    EMAIL = "email"
    TELEFONE = "telefone"
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"

class Alvo(Base):
    __tablename__ = "alvos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(200), nullable=False)
    contato = Column(String(200), nullable=False, index=True)
    tipo_contato = Column(Enum(TipoContato), nullable=False)
    
    campanha_id = Column(UUID(as_uuid=True), ForeignKey("campanhas.id", ondelete="CASCADE"), nullable=False)
    
    metadados = Column(JSON, nullable=True)  # Para dados extras: cargo, rede social, etc.
    ativo = Column(Boolean, default=True)
    
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento com campanha
    # campanha = relationship("Campanha", back_populates="alvos")
    
    def __repr__(self):
        return f"<Alvo {self.nome} ({self.contato})>"