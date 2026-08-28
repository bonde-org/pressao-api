from datetime import datetime

from pydantic import UUID4, BaseModel, Field, field_validator


class CampanhaBase(BaseModel):
    nome: str = Field(..., min_length=3, max_length=200, description="Nome da campanha")
    descricao: str | None = Field(None, description="Descrição da campanha")
    dominios_permitidos: list[str] | None = Field(
        default=[], description="Domínios autorizados para acessar esta campanha"
    )
    ativa: bool = Field(default=True, description="Se a campanha está ativa")

    @field_validator("dominios_permitidos", mode="before")
    @classmethod
    def validate_dominios(cls, v):
        """Garante que dominios_permitidos seja sempre uma lista"""
        if v is None:
            return []
        return v


class CampanhaCreate(CampanhaBase):
    pass


class CampanhaUpdate(BaseModel):
    nome: str | None = Field(None, min_length=3, max_length=200)
    descricao: str | None = None
    dominios_permitidos: list[str] | None = None
    ativa: bool | None = None

    @field_validator("dominios_permitidos", mode="before")
    @classmethod
    def validate_dominios(cls, v):
        if v is None:
            return None
        return v


class CampanhaResponse(CampanhaBase):
    id: UUID4
    acoes_confirmadas: int = Field(
        default=0, description="Total de ações confirmadas na campanha"
    )
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
