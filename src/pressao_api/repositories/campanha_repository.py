from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from pressao_api.models.campanha import Campanha

class CampanhaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def criar(self, dados: dict) -> Campanha:
        campanha = Campanha(**dados)
        self.session.add(campanha)
        await self.session.flush()
        return campanha
    
    async def buscar_por_id(self, campanha_id: UUID) -> Optional[Campanha]:
        query = select(Campanha).where(Campanha.id == campanha_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def buscar_por_nome(self, nome: str) -> Optional[Campanha]:
        query = select(Campanha).where(Campanha.nome == nome)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def listar_todas(self, ativa: Optional[bool] = None) -> List[Campanha]:
        query = select(Campanha)
        if ativa is not None:
            query = query.where(Campanha.ativa == ativa)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def atualizar(self, campanha_id: UUID, dados: dict) -> Optional[Campanha]:
        campanha = await self.buscar_por_id(campanha_id)
        if not campanha:
            return None
        
        for key, value in dados.items():
            if value is not None:
                setattr(campanha, key, value)
        
        await self.session.flush()
        return campanha
    
    async def deletar(self, campanha_id: UUID) -> bool:
        campanha = await self.buscar_por_id(campanha_id)
        if not campanha:
            return False
        
        await self.session.delete(campanha)
        await self.session.flush()
        return True