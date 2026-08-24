from pressao_api.repositories.campanha_repository import CampanhaRepository
from pressao_api.schemas.acao import StatusAcaoEnum


async def incrementar_contador_se_confirmada(
    acao,
    status_anterior: str,
    campanha_repo: CampanhaRepository,
) -> int | None:
    """
    Incrementa contador SOMENTE na transição para CONCLUIDA.
    Retorna novo total ou None se não incrementou.
    """
    if status_anterior == StatusAcaoEnum.CONCLUIDA:
        return None
    if acao.status != StatusAcaoEnum.CONCLUIDA:
        return None
    return await campanha_repo.incrementar_acoes_confirmadas(acao.campanha_id)
