from sqlalchemy import Column, String, DateTime, Text, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from pressao_api.core.database import Base

class Campanha(Base):
    __tablename__ = "campanhas"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(200), nullable=False, index=True)
    descricao = Column(Text, nullable=True)
    dominios_permitidos = Column(JSON, nullable=True, default=list)
    ativa = Column(Boolean, default=True)
    
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento com alvos (lazy loading)
    # alvos = relationship("Alvo", back_populates="campanha")
    
    def __repr__(self):
        return f"<Campanha {self.nome} ({self.id})>"