from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select, update
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

    async def buscar_por_sessao_sem_ativista(self, sessao_id: str) -> list[Acao]:
        """Busca ações não-anônimas de uma sessão que ainda não têm dados de ativista."""
        query = select(Acao).where(
            Acao.sessao_id == sessao_id,
            Acao.anonimo.is_(False),
            Acao.ativista_nome.is_(None),
            Acao.ativista_email.is_(None),
            Acao.ativista_telefone.is_(None),
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def atualizar_ativista_por_sessao(
        self,
        sessao_id: str,
        ativista_nome: str | None = None,
        ativista_email: str | None = None,
        ativista_telefone: str | None = None,
    ) -> int:
        """Atualiza dados do ativista em ações não-anônimas da sessão sem ativista.

        Não seta ativista_preenchido_em — apenas a ação onde o ativista
        preencheu o formulário recebe esse timestamp.
        """
        dados = {}
        if ativista_nome:
            dados["ativista_nome"] = ativista_nome
        if ativista_email:
            dados["ativista_email"] = ativista_email
        if ativista_telefone:
            dados["ativista_telefone"] = ativista_telefone

        if not dados:
            return 0

        stmt = (
            update(Acao)
            .where(
                Acao.sessao_id == sessao_id,
                Acao.anonimo.is_(False),
                Acao.ativista_nome.is_(None),
                Acao.ativista_email.is_(None),
                Acao.ativista_telefone.is_(None),
            )
            .values(**dados)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        logger.info(
            "Ativista atualizado retroativamente",
            sessao_id=sessao_id,
            acoes_atualizadas=result.rowcount,
        )
        return result.rowcount
