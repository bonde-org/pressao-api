from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pressao_api.models.alvo import Alvo
from pressao_api.models.alvo_membro import AlvoMembro


class AlvoMembroRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def listar_membro_ids(self, agregado_id: UUID) -> list[UUID]:
        query = select(AlvoMembro.membro_id).where(AlvoMembro.agregado_id == agregado_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def contar_membros(self, agregado_id: UUID) -> int:
        query = (
            select(func.count())
            .select_from(AlvoMembro)
            .where(AlvoMembro.agregado_id == agregado_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one()

    async def listar_membros_alvos(self, agregado_id: UUID) -> list[Alvo]:
        query = (
            select(Alvo)
            .join(AlvoMembro, AlvoMembro.membro_id == Alvo.id)
            .where(AlvoMembro.agregado_id == agregado_id, Alvo.ativo.is_(True))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def sincronizar(self, agregado_id: UUID, membro_ids: list[UUID]) -> int:
        novos = set(membro_ids)
        existentes = set(await self.listar_membro_ids(agregado_id))

        remover = existentes - novos
        adicionar = novos - existentes

        if remover:
            await self.session.execute(
                delete(AlvoMembro).where(
                    AlvoMembro.agregado_id == agregado_id,
                    AlvoMembro.membro_id.in_(remover),
                )
            )

        for membro_id in adicionar:
            self.session.add(AlvoMembro(agregado_id=agregado_id, membro_id=membro_id))

        await self.session.flush()
        return len(novos)
