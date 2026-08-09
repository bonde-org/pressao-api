from pydantic import BaseModel, Field, UUID4, model_validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pressao_api.utils.validadores import validar_email, validar_telefone

class TipoContato(str, Enum):
    EMAIL = "email"
    TELEFONE = "telefone"
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"

class AlvoBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=200, description="Nome do alvo")
    contato: str = Field(..., max_length=200, description="Contato (email ou telefone)")
    tipo_contato: TipoContato = Field(..., description="Tipo de contato")
    metadados: Optional[Dict[str, Any]] = Field(None, description="Dados extras do alvo")
    ativo: bool = Field(default=True, description="Se o alvo está ativo")

class AlvoCreate(AlvoBase):
    campanha_id: UUID4 = Field(..., description="ID da campanha")
    
    @model_validator(mode='after')
    def validate_contato(self) -> 'AlvoCreate':
        """Valida o contato baseado no tipo após a criação do modelo"""
        if self.tipo_contato == TipoContato.EMAIL:
            if not validar_email(self.contato):
                raise ValueError('Formato de e-mail inválido')
        elif self.tipo_contato == TipoContato.TELEFONE:
            if not validar_telefone(self.contato):
                raise ValueError('Formato de telefone inválido')
        # WhatsApp e Instagram não têm validação específica
        return self

class AlvoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=200)
    contato: Optional[str] = Field(None, max_length=200)
    tipo_contato: Optional[TipoContato] = None
    metadados: Optional[Dict[str, Any]] = None
    ativo: Optional[bool] = None

class AlvoResponse(AlvoBase):
    id: UUID4
    campanha_id: UUID4
    criado_em: datetime
    atualizado_em: datetime
    
    class Config:
        from_attributes = True