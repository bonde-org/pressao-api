from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from pressao_api.models.ligacao import Ligacao


class LigacaoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def criar(self, dados: dict[str, Any]) -> Ligacao:
        ligacao = Ligacao(**dados)
        self.session.add(ligacao)
        await self.session.flush()
        return ligacao

    async def buscar_por_id(self, ligacao_id: UUID) -> Ligacao | None:
        query = select(Ligacao).where(Ligacao.id == ligacao_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def salvar(self, ligacao: Ligacao) -> Ligacao:
        await self.session.merge(ligacao)
        await self.session.flush()
        return ligacao

    async def listar_por_acao(self, acao_id: UUID) -> list[Ligacao]:
        query = (
            select(Ligacao)
            .where(Ligacao.acao_id == acao_id)
            .order_by(Ligacao.criado_em, Ligacao.id)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def buscar_ultima_por_acao(self, acao_id: UUID) -> Ligacao | None:
        ligacoes = await self.listar_por_acao(acao_id)
        return ligacoes[-1] if ligacoes else None

    async def contar_por_alvo(self, alvo_ids: list[UUID]) -> dict[UUID, int]:
        """Ligações por alvo, sem contar as que falharam do lado do ativista."""
        if not alvo_ids:
            return {}
        query = (
            select(Ligacao.alvo_id, func.count())
            .where(
                Ligacao.alvo_id.in_(alvo_ids),
                or_(Ligacao.origem_falha.is_(None), Ligacao.origem_falha != "ativista"),
            )
            .group_by(Ligacao.alvo_id)
        )
        result = await self.session.execute(query)
        return {alvo_id: int(total) for alvo_id, total in result.all()}
