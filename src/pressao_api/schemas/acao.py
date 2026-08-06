from pydantic import BaseModel, Field, UUID4
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

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
class CriarAcaoRequest(BaseModel):
    campanha_id: UUID4
    alvo_id: UUID4
    canal: CanalEnum
    template_id: Optional[UUID4] = None
    
    class Config:
        use_enum_values = True

class ConfirmarAcaoRequest(BaseModel):
    pass  # Sem dados no corpo

# Response schemas
class ProximoPassoResponse(BaseModel):
    tipo: ProximoPassoTipoEnum
    instrucao: str
    dados: Dict[str, Any]

class RespostaAcaoResponse(BaseModel):
    acao_id: UUID4
    ativista_id: str
    campanha_id: UUID4
    alvo_id: UUID4
    status_atual: StatusAcaoEnum
    proximo_passo: ProximoPassoResponse

class AcaoDetailResponse(BaseModel):
    id: UUID4
    ativista_id: str
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