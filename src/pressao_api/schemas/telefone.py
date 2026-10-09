from datetime import datetime
from enum import Enum

from pydantic import UUID4, BaseModel, Field, field_validator

from pressao_api.schemas.acao import StatusAcaoEnum
from pressao_api.schemas.alvo import AlvoMembroTelefonePublico
from pressao_api.schemas.template import TemplateSorteadoResponse
from pressao_api.utils.validadores import normalizar_telefone_e164


class PernaLigacaoEnum(str, Enum):
    ATIVISTA = "ativista"
    ALVO = "alvo"


class StatusChamadaEnum(str, Enum):
    """Status de chamada no vocabulário do Twilio (`CallStatus` / `DialCallStatus`)."""

    QUEUED = "queued"
    INITIATED = "initiated"
    RINGING = "ringing"
    IN_PROGRESS = "in-progress"
    ANSWERED = "answered"
    COMPLETED = "completed"
    BUSY = "busy"
    NO_ANSWER = "no-answer"
    FAILED = "failed"
    CANCELED = "canceled"


class EtapaLigacaoEnum(str, Enum):
    INICIANDO = "INICIANDO"
    CHAMANDO_ATIVISTA = "CHAMANDO_ATIVISTA"
    CHAMANDO_ALVO = "CHAMANDO_ALVO"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    CONCLUIDA = "CONCLUIDA"
    FALHA = "FALHA"


class OrigemFalhaEnum(str, Enum):
    ATIVISTA = "ativista"
    ALVO = "alvo"


class ResultadoLigacao(BaseModel):
    """Resultado do pedido de ligação ao provedor."""

    sucesso: bool
    call_id: str | None = None
    dry_run: bool = False
    provedor: str = Field(description="dry_run ou twilio")
    erro: str | None = None


class EventoLigacao(BaseModel):
    """Evento de status de uma perna da ligação, independente do provedor."""

    ligacao_id: UUID4
    perna: PernaLigacaoEnum
    status: StatusChamadaEnum
    duracao_seg: int | None = Field(None, ge=0)
    call_id: str | None = Field(None, max_length=64)


class NovaTentativaLigacaoRequest(BaseModel):
    membro_id: UUID4 | None = Field(None, description="Membro escolhido pelo ativista")
    telefone: str | None = Field(None, max_length=20, description="Novo telefone do ativista")

    @field_validator("telefone")
    @classmethod
    def validate_telefone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return normalizar_telefone_e164(v)


class ProximoMembroResponse(BaseModel):
    membro: AlvoMembroTelefonePublico
    template: TemplateSorteadoResponse | None = None


class LigacaoStatusResponse(BaseModel):
    ligacao_id: UUID4
    acao_id: UUID4
    acao_status: StatusAcaoEnum
    etapa: EtapaLigacaoEnum
    origem_falha: OrigemFalhaEnum | None = None
    motivo_falha: str | None = None
    alvo: AlvoMembroTelefonePublico
    selecao: str
    duracao_seg: int | None = None
    tentativas: int
    iniciada_em: datetime | None = None
    alvo_atendeu_em: datetime | None = None
    finalizada_em: datetime | None = None
