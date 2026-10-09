from datetime import datetime

from pydantic import UUID4, BaseModel, Field, field_validator

from pressao_api.utils.validadores import normalizar_telefone_e164, telefone_toll_free_br


def _validar_telefone_origem(v: str | None) -> str | None:
    if v is None or not v.strip():
        return None
    telefone = normalizar_telefone_e164(v)
    if telefone_toll_free_br(telefone):
        raise ValueError("Número 0800 não pode originar ligações; use um número local do Twilio")
    return telefone


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
