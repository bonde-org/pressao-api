from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from pressao_api.models.acao import Acao
from pressao_api.models.campanha import Campanha


class CampanhaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def criar(self, dados: dict) -> Campanha:
        campanha = Campanha(**dados)
        self.session.add(campanha)
        await self.session.flush()
        return campanha

    async def buscar_por_id(self, campanha_id: UUID) -> Campanha | None:
        query = select(Campanha).where(Campanha.id == campanha_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def buscar_por_nome(self, nome: str) -> Campanha | None:
        query = select(Campanha).where(Campanha.nome == nome)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def listar_todas(self, ativa: bool | None = None) -> list[Campanha]:
        query = select(Campanha)
        if ativa is not None:
            query = query.where(Campanha.ativa == ativa)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def atualizar(self, campanha_id: UUID, dados: dict) -> Campanha | None:
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

    async def incrementar_acoes_confirmadas(self, campanha_id: UUID) -> int:
        stmt = (
            update(Campanha)
            .where(Campanha.id == campanha_id)
            .values(acoes_confirmadas=Campanha.acoes_confirmadas + 1)
            .returning(Campanha.acoes_confirmadas)
        )
        result = await self.session.execute(stmt)
        valor = result.scalar_one()
        await self.session.flush()
        return int(valor)

    async def contar_acoes_confirmadas_real(self, campanha_id: UUID) -> int:
        stmt = select(func.count()).where(
            Acao.campanha_id == campanha_id,
            Acao.status == "CONCLUIDA",
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def reconciliar_acoes_confirmadas(self, campanha_id: UUID) -> tuple[int, int]:
        campanha = await self.buscar_por_id(campanha_id)
        if not campanha:
            return (0, 0)
        antes = int(campanha.acoes_confirmadas or 0)
        depois = await self.contar_acoes_confirmadas_real(campanha_id)
        campanha.acoes_confirmadas = depois
        await self.session.flush()
        return (antes, depois)
