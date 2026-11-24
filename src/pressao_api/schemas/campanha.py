from datetime import datetime
from typing import Literal

from pydantic import UUID4, BaseModel, Field, field_validator

from pressao_api.utils.validadores import (
    normalizar_telefone_e164,
    telefone_toll_free_br,
    validar_email,
)


def _validar_telefone_origem(v: str | None) -> str | None:
    if v is None or not v.strip():
        return None
    telefone = normalizar_telefone_e164(v)
    if telefone_toll_free_br(telefone):
        raise ValueError("Número 0800 não pode originar ligações; use um número local do Twilio")
    return telefone


class ActionNetworkConfig(BaseModel):
    """Contato criado/atualizado no Action Network quando o ativista age na campanha."""

    tags: list[str] = Field(..., min_length=1, description="Tags aplicadas ao contato")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        tags = [t.strip() for t in v if t and t.strip()]
        if not tags:
            raise ValueError("Informe ao menos uma tag")
        if any(len(t) > 100 for t in tags):
            raise ValueError("Cada tag deve ter no máximo 100 caracteres")
        return list(dict.fromkeys(tags))


class ConfirmacaoEmailConfig(BaseModel):
    """E-mail de confirmação enviado ao ativista após a primeira ação na campanha."""

    remetente_nome: str = Field(..., min_length=1, max_length=100)
    remetente_email: str = Field(..., max_length=200)
    assunto: str = Field(..., min_length=1, max_length=200)
    texto: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Texto puro; parágrafos separados por linha em branco. {nome} = 1º nome",
    )

    @field_validator("remetente_email")
    @classmethod
    def validate_remetente_email(cls, v: str) -> str:
        v = v.strip()
        if not validar_email(v):
            raise ValueError("E-mail do remetente inválido")
        return v


class PosAcaoConfig(BaseModel):
    """O que acontece depois que o ativista conclui uma ação na campanha."""

    canais: list[Literal["email", "telefone", "instagram", "tiktok", "whatsapp"]] = Field(
        default=["email"], description="Canais cuja ação dispara o pós-ação"
    )
    actionnetwork: ActionNetworkConfig | None = None
    confirmacao_email: ConfirmacaoEmailConfig | None = None


class CampanhaBase(BaseModel):
    nome: str = Field(..., min_length=3, max_length=200, description="Nome da campanha")
    descricao: str | None = Field(None, description="Descrição da campanha")
    dominios_permitidos: list[str] | None = Field(
        default=[], description="Domínios autorizados para acessar esta campanha"
    )
    ativa: bool = Field(default=True, description="Se a campanha está ativa")
    telefone_origem: str | None = Field(
        None,
        max_length=20,
        description=(
            "Número Twilio (E.164) da campanha: liga para o ativista e aparece para o alvo "
            "no canal telefone"
        ),
    )
    pos_acao: PosAcaoConfig | None = Field(
        None, description="Action Network e e-mail de confirmação do ativista"
    )

    @field_validator("dominios_permitidos", mode="before")
    @classmethod
    def validate_dominios(cls, v):
        """Garante que dominios_permitidos seja sempre uma lista"""
        if v is None:
            return []
        return v

    @field_validator("telefone_origem")
    @classmethod
    def validate_telefone_origem(cls, v: str | None) -> str | None:
        return _validar_telefone_origem(v)


class CampanhaCreate(CampanhaBase):
    pass


class CampanhaUpdate(BaseModel):
    nome: str | None = Field(None, min_length=3, max_length=200)
    descricao: str | None = None
    dominios_permitidos: list[str] | None = None
    ativa: bool | None = None
    telefone_origem: str | None = Field(None, max_length=20)
    pos_acao: PosAcaoConfig | None = None

    @field_validator("dominios_permitidos", mode="before")
    @classmethod
    def validate_dominios(cls, v):
        if v is None:
            return None
        return v

    @field_validator("telefone_origem")
    @classmethod
    def validate_telefone_origem(cls, v: str | None) -> str | None:
        return _validar_telefone_origem(v)


class CampanhaResponse(CampanhaBase):
    id: UUID4
    acoes_confirmadas: int = Field(default=0, description="Total de ações confirmadas na campanha")
    criado_em: datetime
    atualizado_em: datetime

    class Config:
        from_attributes = True


class ConfirmacaoContadorResponse(BaseModel):
    acoes_confirmadas: int


class ReconciliarContadorResponse(BaseModel):
    antes: int
    depois: int
    divergencia: int
