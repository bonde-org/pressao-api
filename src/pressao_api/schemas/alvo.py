from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import UUID4, BaseModel, Field, model_validator

from pressao_api.schemas.template import TemplateSorteadoResponse
from pressao_api.utils.validadores import validar_email, validar_telefone


class TipoContato(str, Enum):
    EMAIL = "email"
    TELEFONE = "telefone"
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"


class ModoAlvo(str, Enum):
    INDIVIDUAL = "individual"
    AGREGADO = "agregado"


class AlvoBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=200, description="Nome do alvo")
    contato: str = Field(..., max_length=200, description="Contato (email ou telefone)")
    tipo_contato: TipoContato = Field(..., description="Tipo de contato")
    metadados: dict[str, Any] | None = Field(None, description="Dados extras do alvo")
    ativo: bool = Field(default=True, description="Se o alvo está ativo")


class AlvoCreate(AlvoBase):
    campanha_id: UUID4 = Field(..., description="ID da campanha")

    @model_validator(mode="after")
    def validate_contato(self) -> "AlvoCreate":
        """Valida o contato baseado no tipo após a criação do modelo"""
        if self.tipo_contato == TipoContato.EMAIL and not validar_email(self.contato):
            raise ValueError("Formato de e-mail inválido")
        elif self.tipo_contato == TipoContato.TELEFONE and not validar_telefone(self.contato):
            raise ValueError("Formato de telefone inválido")
        # WhatsApp e Instagram não têm validação específica
        return self


class AlvoUpdate(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=200)
    contato: str | None = Field(None, max_length=200)
    tipo_contato: TipoContato | None = None
    metadados: dict[str, Any] | None = None
    ativo: bool | None = None


class AlvoResponse(AlvoBase):
    id: UUID4
    campanha_id: UUID4
    modo: ModoAlvo = ModoAlvo.INDIVIDUAL
    total_membros: int | None = Field(
        None, description="Quantidade de membros (apenas alvo agregado de e-mail)"
    )
    criado_em: datetime
    atualizado_em: datetime
    template: TemplateSorteadoResponse | None = Field(
        None, description="Template sorteado para este alvo (apenas canal email)"
    )

    class Config:
        from_attributes = True
