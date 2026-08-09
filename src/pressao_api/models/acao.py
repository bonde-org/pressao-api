from sqlalchemy import Column, String, DateTime, Enum, JSON, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from pressao_api.core.database import Base

class Acao(Base):
    """Modelo de Ação de Pressão."""
    
    __tablename__ = "acoes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Ativista (opcional para anônimos)
    ativista_id = Column(String(100), nullable=True, index=True)
    ativista_nome = Column(String(200), nullable=True)
    ativista_email = Column(String(200), nullable=True, index=True)
    ativista_telefone = Column(String(20), nullable=True, index=True)
    anonimo = Column(Boolean, nullable=False, default=False)
    
    # Ação
    campanha_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    alvo_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    canal = Column(String(20), nullable=False)
    template_id = Column(UUID(as_uuid=True), nullable=True)
    
    status = Column(
        Enum(
            "PROCESSANDO",
            "AGUARDANDO_ACAO_HUMANA",
            "CONCLUIDA",
            "FALHA",
            name="status_acao"
        ),
        default="PROCESSANDO",
        nullable=False
    )
    
    proximo_passo_tipo = Column(
        Enum(
            "WEBHOOK_AGUARDAR",
            "REDIRECIONAR_LINK",
            "EXIBIR_TEXTO_E_ABRIR_PERFIL",
            "FINALIZADO",
            name="proximo_passo_tipo"
        ),
        nullable=True
    )
    proximo_passo_instrucao = Column(String(500), nullable=True)
    proximo_passo_dados = Column(JSON, nullable=True)
    
    metrica_qualidade = Column(
        Enum("suspeita", "alta", "media", "baixa", name="metrica_qualidade"),
        nullable=True
    )
    tempo_resposta_seg = Column(Integer, nullable=True)
    
    confirmado_em = Column(DateTime, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    # campanha = relationship("Campanha", back_populates="acoes")
    # alvo = relationship("Alvo", back_populates="acoes")
    
    def __repr__(self):
        return f"<Acao {self.id} - {self.canal}>"