from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pressao_api.models.alvo import Alvo, ModoAlvo, TipoContato
from pressao_api.repositories.alvo_membro_repository import AlvoMembroRepository
from pressao_api.repositories.alvo_repository import AlvoRepository

NOME_AGREGADO_EMAIL = "Pressionar por E-mail"
NOME_AGREGADO_TELEFONE = "Pressionar por Telefone"

TIPOS_AGREGADOS = (TipoContato.EMAIL, TipoContato.TELEFONE)


def _contato_agregado(campanha_id: UUID) -> str:
    return f"agregado.{campanha_id}@pressao.local"


def _contato_agregado_telefone(campanha_id: UUID) -> str:
    return f"agregado-telefone.{campanha_id}"


def _dados_agregado(campanha_id: UUID, tipo: TipoContato) -> dict[str, Any]:
    if tipo == TipoContato.TELEFONE:
        nome = NOME_AGREGADO_TELEFONE
        contato = _contato_agregado_telefone(campanha_id)
        metadados = {"agregado_telefone": True}
    else:
        nome = NOME_AGREGADO_EMAIL
        contato = _contato_agregado(campanha_id)
        metadados = {"agregado_email": True}
    return {
        "campanha_id": campanha_id,
        "nome": nome,
        "contato": contato,
        "tipo_contato": tipo,
        "modo": ModoAlvo.AGREGADO,
        "metadados": metadados,
        "ativo": True,
    }


def membro_telefone_publico(alvo: Alvo) -> dict[str, Any]:
    """Dados exibíveis de um membro de telefone (sem o número)."""
    metadados = alvo.metadados or {}
    return {
        "id": alvo.id,
        "nome": alvo.nome,
        "cargo": metadados.get("cargo"),
        "partido": metadados.get("partido"),
    }


class AlvoAgregadoService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.alvo_repo = AlvoRepository(session)
        self.membro_repo = AlvoMembroRepository(session)

    async def buscar_agregado(self, campanha_id: UUID, tipo: TipoContato) -> Alvo | None:
        query = select(Alvo).where(
            Alvo.campanha_id == campanha_id,
            Alvo.tipo_contato == tipo,
            Alvo.modo == ModoAlvo.AGREGADO,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def garantir_agregado(self, campanha_id: UUID, tipo: TipoContato) -> Alvo:
        agregado = await self.buscar_agregado(campanha_id, tipo)
        if agregado:
            return agregado
        return await self.alvo_repo.criar(_dados_agregado(campanha_id, tipo))

    async def buscar_agregado_email(self, campanha_id: UUID) -> Alvo | None:
        return await self.buscar_agregado(campanha_id, TipoContato.EMAIL)

    async def garantir_agregado_email(self, campanha_id: UUID) -> Alvo:
        return await self.garantir_agregado(campanha_id, TipoContato.EMAIL)

    async def _listar_individuais(
        self, campanha_id: UUID, tipo: TipoContato, ativo: bool | None = None
    ) -> list[Alvo]:
        alvos = await self.alvo_repo.listar_por_campanha(campanha_id, ativo)
        return [
            alvo
            for alvo in alvos
            if alvo.tipo_contato == tipo and alvo.modo == ModoAlvo.INDIVIDUAL
        ]

    async def sincronizar_membros_tipo(self, campanha_id: UUID, tipo: TipoContato) -> int:
        membros = await self._listar_individuais(campanha_id, tipo, ativo=True)
        if tipo == TipoContato.TELEFONE and not membros:
            agregado = await self.buscar_agregado(campanha_id, tipo)
            if agregado is None:
                return 0
        else:
            agregado = await self.garantir_agregado(campanha_id, tipo)
        return await self.membro_repo.sincronizar(agregado.id, [m.id for m in membros])

    async def sincronizar_membros(self, campanha_id: UUID) -> int:
        """Sincroniza o agregado de e-mail (retorna o total dele) e o de telefone."""
        await self.sincronizar_membros_tipo(campanha_id, TipoContato.TELEFONE)
        return await self.sincronizar_membros_tipo(campanha_id, TipoContato.EMAIL)

    async def listar_para_exibicao(
        self, campanha_id: UUID, ativo: bool | None = None
    ) -> list[Alvo]:
        await self.sincronizar_membros(campanha_id)

        resultado: list[Alvo] = []
        for tipo in TIPOS_AGREGADOS:
            agregado = await self.buscar_agregado(campanha_id, tipo)
            if not agregado:
                continue
            membros_count = await self.membro_repo.contar_membros(agregado.id)
            if membros_count > 0 and (ativo is None or agregado.ativo == ativo):
                resultado.append(agregado)

        todos = await self.alvo_repo.listar_por_campanha(campanha_id, ativo)
        resultado.extend(
            alvo
            for alvo in todos
            if alvo.modo != ModoAlvo.AGREGADO and alvo.tipo_contato not in TIPOS_AGREGADOS
        )
        return resultado

    async def contar_membros_agregado(self, agregado_id: UUID) -> int:
        return await self.membro_repo.contar_membros(agregado_id)

    async def listar_nomes_membros(self, agregado_id: UUID) -> list[str]:
        """Nomes dos membros ativos do agregado, em ordem alfabética (sem contatos)."""
        membros = await self.membro_repo.listar_membros_alvos(agregado_id)
        return sorted((m.nome for m in membros), key=str.casefold)

    async def listar_membros_publicos(self, agregado: Alvo) -> list[dict[str, Any]]:
        """Membros ativos em ordem alfabética: e-mail só com nome; telefone com id/cargo/partido."""
        membros = await self.membro_repo.listar_membros_alvos(agregado.id)
        membros = sorted(membros, key=lambda m: m.nome.casefold())
        if agregado.tipo_contato == TipoContato.TELEFONE:
            return [membro_telefone_publico(m) for m in membros]
        return [{"nome": m.nome} for m in membros]
