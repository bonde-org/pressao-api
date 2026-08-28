from datetime import datetime

from pydantic import UUID4, BaseModel, Field

from pressao_api.schemas.acao import CanalEnum


class TemplateBase(BaseModel):
    canal: CanalEnum = Field(..., description="Canal ao qual o template se aplica")
    titulo: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Título do template; usado como assunto no canal email",
    )
    conteudo: str = Field(
        ..., min_length=1, description="Corpo da mensagem, pode conter placeholders"
    )
    ativo: bool = Field(default=True, description="Se o template entra no sorteio")


class TemplateCreate(TemplateBase):
    campanha_id: UUID4 = Field(..., description="ID da campanha")


class TemplateUpdate(BaseModel):
    canal: CanalEnum | None = None
    titulo: str | None = Field(None, min_length=1, max_length=255)
    conteudo: str | None = Field(None, min_length=1)
    ativo: bool | None = None


class TemplateResponse(TemplateBase):
    id: UUID4
    campanha_id: UUID4
    criado_em: datetime
    atualizado_em: datetime

    class Config:
        from_attributes = True


class TemplateSorteadoResponse(BaseModel):
    """Template sorteado para um alvo no momento da consulta."""

    id: UUID4
    canal: CanalEnum
    titulo: str
    conteudo: str

    class Config:
        from_attributes = True
