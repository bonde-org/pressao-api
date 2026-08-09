from pydantic import BaseModel, Field, UUID4, field_validator, model_validator
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pressao_api.utils.validadores import validar_email, validar_telefone

class CanalEnum(str, Enum):
    EMAIL = "email"
    TELEFONE = "telefone"
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"

class StatusAcaoEnum(str, Enum):
    PROCESSANDO = "PROCESSANDO"
    AGUARDANDO_ACAO_HUMANA = "AGUARDANDO_ACAO_HUMANA"
    CONCLUIDA = "CONCLUIDA"
    FALHA = "FALHA"

class ProximoPassoTipoEnum(str, Enum):
    WEBHOOK_AGUARDAR = "WEBHOOK_AGUARDAR"
    REDIRECIONAR_LINK = "REDIRECIONAR_LINK"
    EXIBIR_TEXTO_E_ABRIR_PERFIL = "EXIBIR_TEXTO_E_ABRIR_PERFIL"
    FINALIZADO = "FINALIZADO"

class MetricaQualidadeEnum(str, Enum):
    SUSPEITA = "suspeita"
    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"

# Request schemas

class AtivistaInfo(BaseModel):
    nome: Optional[str] = Field(None, max_length=200, description="Nome completo do ativista")
    email: Optional[str] = Field(None, max_length=200, description="Email do ativista")
    telefone: Optional[str] = Field(None, max_length=20, description="Telefone do ativista")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v and not validar_email(v):
            raise ValueError('Formato de e-mail inválido')
        return v
    
    @field_validator('telefone')
    @classmethod
    def validate_telefone(cls, v: Optional[str]) -> Optional[str]:
        if v and not validar_telefone(v):
            raise ValueError('Formato de telefone inválido. Use: (11) 99999-9999 ou 11999999999')
        return v

class CriarAcaoRequest(BaseModel):
    campanha_id: UUID4
    alvo_id: UUID4
    canal: CanalEnum
    template_id: Optional[UUID4] = None
    
    ativista: Optional[AtivistaInfo] = None
    anonimo: bool = False
    
    @model_validator(mode='after')
    def validate_identificacao(self) -> 'CriarAcaoRequest':
        """Valida que pelo menos um identificador foi fornecido"""
        if self.anonimo:
            return self
        
        if not self.ativista:
            return self
        
        if not self.ativista.email and not self.ativista.telefone:
            raise ValueError('É necessário fornecer email ou telefone do ativista')
        
        return self

# Response schemas
class ProximoPassoResponse(BaseModel):
    tipo: ProximoPassoTipoEnum
    instrucao: str
    dados: Dict[str, Any]

class RespostaAcaoResponse(BaseModel):
    acao_id: UUID4
    ativista_id: Optional[str] = None
    ativista_nome: Optional[str] = None
    ativista_email: Optional[str] = None
    ativista_telefone: Optional[str] = None
    anonimo: bool = False  # ← IMPORTANTE!
    campanha_id: UUID4
    alvo_id: UUID4
    status_atual: StatusAcaoEnum
    proximo_passo: ProximoPassoResponse

class AcaoDetailResponse(BaseModel):
    id: UUID4
    ativista_id: str
    ativista_nome: Optional[str] = None
    ativista_email: Optional[str] = None
    ativista_telefone: Optional[str] = None
    anonimo: bool = False
    campanha_id: UUID4
    alvo_id: UUID4
    canal: str
    template_id: Optional[UUID4]
    status: StatusAcaoEnum
    metrica_qualidade: Optional[MetricaQualidadeEnum]
    tempo_resposta_seg: Optional[int]
    confirmado_em: Optional[datetime]
    criado_em: datetime
    atualizado_em: datetime
    
    class Config:
        from_attributes = True

class AcaoStatusResponse(BaseModel):
    id: UUID4
    status: StatusAcaoEnum
    metrica_qualidade: Optional[MetricaQualidadeEnum]
    confirmado_em: Optional[datetime]