from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pressao_api.models.acao import Acao

logger = structlog.get_logger()

class AcaoRepository:
    """Repositório para operações com Ação."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def criar(self, data: dict[str, Any]) -> Acao:
        """Cria uma nova ação."""
        acao = Acao(**data)
        self.session.add(acao)
        await self.session.flush()
        return acao
    
    async def buscar_por_id(self, acao_id: UUID) -> Acao | None:
        """Busca ação por ID."""
        query = select(Acao).where(Acao.id == acao_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def buscar_por_ativista(self, ativista_id: str) -> list[Acao]:
        """Busca ações de um ativista."""
        query = select(Acao).where(Acao.ativista_id == ativista_id)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def buscar_por_email(self, email: str) -> list[Acao]:
        """Busca ações por email do ativista"""
        query = select(Acao).where(Acao.ativista_email == email)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def salvar(self, acao: Acao) -> Acao:
        """Salva alterações na ação."""
        await self.session.merge(acao)
        await self.session.flush()
        return acao