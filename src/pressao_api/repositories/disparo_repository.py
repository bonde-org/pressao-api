from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pressao_api.models.disparo import Disparo


class DisparoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def criar(self, dados: dict[str, Any]) -> Disparo:
        disparo = Disparo(**dados)
        self.session.add(disparo)
        await self.session.flush()
        return disparo

    async def buscar_por_id(self, disparo_id: UUID) -> Disparo | None:
        query = select(Disparo).where(Disparo.id == disparo_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def salvar(self, disparo: Disparo) -> Disparo:
        await self.session.merge(disparo)
        await self.session.flush()
        return disparo

    async def listar_por_acao(self, acao_id: UUID) -> list[Disparo]:
        query = select(Disparo).where(Disparo.acao_id == acao_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def resumo_por_acao(self, acao_id: UUID) -> dict[str, int]:
        disparos = await self.listar_por_acao(acao_id)
        total = len(disparos)
        enviados = sum(1 for d in disparos if d.status == "ENVIADO")
        entregues = sum(1 for d in disparos if d.status == "ENTREGUE")
        falhas = sum(1 for d in disparos if d.status in ("FALHA", "ERRO_ENVIO"))
        return {
            "total": total,
            "enviados": enviados,
            "entregues": entregues,
            "falhas": falhas,
        }
