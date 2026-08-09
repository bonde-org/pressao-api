from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pressao_api.models.alvo import Alvo

class AlvoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def criar(self, dados: dict) -> Alvo:
        alvo = Alvo(**dados)
        self.session.add(alvo)
        await self.session.flush()
        return alvo
    
    async def buscar_por_id(self, alvo_id: UUID) -> Optional[Alvo]:
        query = select(Alvo).where(Alvo.id == alvo_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def listar_por_campanha(self, campanha_id: UUID, ativo: Optional[bool] = None) -> List[Alvo]:
        query = select(Alvo).where(Alvo.campanha_id == campanha_id)
        if ativo is not None:
            query = query.where(Alvo.ativo == ativo)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def buscar_por_contato(self, contato: str) -> List[Alvo]:
        query = select(Alvo).where(Alvo.contato == contato)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def atualizar(self, alvo_id: UUID, dados: dict) -> Optional[Alvo]:
        alvo = await self.buscar_por_id(alvo_id)
        if not alvo:
            return None
        
        for key, value in dados.items():
            if value is not None:
                setattr(alvo, key, value)
        
        await self.session.flush()
        return alvo
    
    async def deletar(self, alvo_id: UUID) -> bool:
        alvo = await self.buscar_por_id(alvo_id)
        if not alvo:
            return False
        
        await self.session.delete(alvo)
        await self.session.flush()
        return True