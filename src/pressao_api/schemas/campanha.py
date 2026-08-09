from pydantic import BaseModel, Field, UUID4, field_validator
from typing import Optional, List
from datetime import datetime

class CampanhaBase(BaseModel):
    nome: str = Field(..., min_length=3, max_length=200, description="Nome da campanha")
    descricao: Optional[str] = Field(None, description="Descrição da campanha")
    dominios_permitidos: Optional[List[str]] = Field(default=[], description="Domínios autorizados para acessar esta campanha")
    ativa: bool = Field(default=True, description="Se a campanha está ativa")
    
    @field_validator('dominios_permitidos', mode='before')
    @classmethod
    def validate_dominios(cls, v):
        """Garante que dominios_permitidos seja sempre uma lista"""
        if v is None:
            return []
        return v

class CampanhaCreate(CampanhaBase):
    pass

class CampanhaUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=3, max_length=200)
    descricao: Optional[str] = None
    dominios_permitidos: Optional[List[str]] = None
    ativa: Optional[bool] = None
    
    @field_validator('dominios_permitidos', mode='before')
    @classmethod
    def validate_dominios(cls, v):
        if v is None:
            return None
        return v

class CampanhaResponse(CampanhaBase):
    id: UUID4
    criado_em: datetime
    atualizado_em: datetime
    
    class Config:
        from_attributes = True