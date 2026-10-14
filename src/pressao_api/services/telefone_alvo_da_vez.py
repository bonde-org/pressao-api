import random
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from pressao_api.models.alvo import Alvo
from pressao_api.repositories.alvo_membro_repository import AlvoMembroRepository
from pressao_api.repositories.ligacao_repository import LigacaoRepository

SELECAO_AUTOMATICA = "automatica"
SELECAO_ATIVISTA = "ativista"


class SemMembrosTelefoneError(ValueError):
    pass


async def escolher_membro(
    session: AsyncSession,
    agregado_id: UUID,
    membro_id: UUID | None = None,
    selecao: str | None = None,
) -> tuple[Alvo, str]:
    """
    Escolhe o membro que recebe a ligação e indica quem escolheu.

    Com `membro_id`, valida que ele é membro ativo do agregado; `selecao` diz se ele veio do
    ativista (padrão) ou do alvo da vez sugerido. Sem ele, pega o membro com menos ligações
    (falhas do lado do ativista não contam); empate é sorteado.
    """
    membros = await AlvoMembroRepository(session).listar_membros_alvos(agregado_id)
    if not membros:
        raise SemMembrosTelefoneError("Nenhum alvo de telefone ativo para esta ação")

    if membro_id is not None:
        for membro in membros:
            if membro.id == membro_id:
                return membro, selecao or SELECAO_ATIVISTA
        raise ValueError("Alvo escolhido não pertence a esta campanha ou está inativo")

    contagem = await LigacaoRepository(session).contar_por_alvo([m.id for m in membros])
    menor = min(contagem.get(m.id, 0) for m in membros)
    candidatos = [m for m in membros if contagem.get(m.id, 0) == menor]
    return random.choice(candidatos), SELECAO_AUTOMATICA
