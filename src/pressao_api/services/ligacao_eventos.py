from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from pressao_api.models.ligacao import ETAPAS_TERMINAIS, Ligacao
from pressao_api.repositories.acao_repository import AcaoRepository
from pressao_api.repositories.campanha_repository import CampanhaRepository
from pressao_api.repositories.disparo_repository import DisparoRepository
from pressao_api.repositories.ligacao_repository import LigacaoRepository
from pressao_api.schemas.acao import ProximoPassoTipoEnum, StatusAcaoEnum
from pressao_api.schemas.telefone import EventoLigacao, PernaLigacaoEnum, StatusChamadaEnum
from pressao_api.services.confirmacao import incrementar_contador_se_confirmada

logger = structlog.get_logger()

PROCESSADO = "processado"
IGNORADO = "ignorado"

STATUS_CHAMANDO = {StatusChamadaEnum.QUEUED, StatusChamadaEnum.INITIATED, StatusChamadaEnum.RINGING}
STATUS_ATENDIDA = {StatusChamadaEnum.IN_PROGRESS, StatusChamadaEnum.ANSWERED}
STATUS_FALHA = {
    StatusChamadaEnum.BUSY,
    StatusChamadaEnum.NO_ANSWER,
    StatusChamadaEnum.FAILED,
    StatusChamadaEnum.CANCELED,
}


class LigacaoNaoEncontradaError(LookupError):
    pass


def _origem_e_motivo(perna: PernaLigacaoEnum, status: StatusChamadaEnum) -> tuple[str, str]:
    """
    Converte a falha de uma perna na origem/motivo exibidos ao ativista.

    - Ativista ocupado é tratado como não atendido (o Figma não tem "ocupado" para o ativista).
    - Perna do alvo cancelada significa que o ativista desligou enquanto o alvo chamava.
    """
    if perna == PernaLigacaoEnum.ATIVISTA:
        motivo = "no-answer" if status == StatusChamadaEnum.BUSY else status.value
        return "ativista", motivo
    if status == StatusChamadaEnum.CANCELED:
        return "ativista", "canceled"
    return "alvo", status.value


class ProcessadorEventosLigacao:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.ligacao_repo = LigacaoRepository(session)
        self.disparo_repo = DisparoRepository(session)
        self.acao_repo = AcaoRepository(session)
        self.campanha_repo = CampanhaRepository(session)

    async def processar(self, evento: EventoLigacao) -> tuple[str, Ligacao]:
        ligacao = await self.ligacao_repo.buscar_por_id(evento.ligacao_id)
        if ligacao is None:
            raise LigacaoNaoEncontradaError("Ligação não encontrada")

        agora = datetime.utcnow()  # noqa: DTZ003
        ligacao.eventos = [
            *(ligacao.eventos or []),
            {
                "perna": evento.perna.value,
                "status": evento.status.value,
                "em": agora.isoformat(),
                "duracao_seg": evento.duracao_seg,
                "call_id": evento.call_id,
            },
        ]

        if ligacao.etapa in ETAPAS_TERMINAIS:
            await self.ligacao_repo.salvar(ligacao)
            return IGNORADO, ligacao

        if evento.perna == PernaLigacaoEnum.ATIVISTA:
            await self._evento_ativista(ligacao, evento, agora)
        else:
            await self._evento_alvo(ligacao, evento, agora)

        await self.ligacao_repo.salvar(ligacao)
        logger.info(
            "Evento de ligação processado",
            ligacao_id=str(ligacao.id),
            perna=evento.perna.value,
            status=evento.status.value,
            etapa=ligacao.etapa,
        )
        return PROCESSADO, ligacao

    async def _evento_ativista(
        self, ligacao: Ligacao, evento: EventoLigacao, agora: datetime
    ) -> None:
        if evento.status in STATUS_CHAMANDO:
            ligacao.etapa = "CHAMANDO_ATIVISTA"
        elif evento.status in STATUS_ATENDIDA:
            ligacao.etapa = "CHAMANDO_ALVO"
        elif evento.status in STATUS_FALHA:
            origem, motivo = _origem_e_motivo(evento.perna, evento.status)
            await self._falhar(ligacao, origem, motivo, agora)
        elif evento.status == StatusChamadaEnum.COMPLETED:
            if ligacao.alvo_atendeu_em is not None:
                await self._concluir(ligacao, evento.duracao_seg, agora)
            elif not self._alvo_discado(ligacao):
                await self._falhar(ligacao, "ativista", "canceled", agora)

    @staticmethod
    def _alvo_discado(ligacao: Ligacao) -> bool:
        """
        Perna do alvo já começou: o status final dela decide o resultado.

        Quando o alvo recusa, o provedor encerra as duas pernas quase juntas e o `completed` do
        ativista pode chegar antes do `no-answer`/`busy` do alvo.
        """
        return any(e.get("perna") == PernaLigacaoEnum.ALVO.value for e in ligacao.eventos or [])

    async def _evento_alvo(self, ligacao: Ligacao, evento: EventoLigacao, agora: datetime) -> None:
        if evento.status in STATUS_CHAMANDO:
            ligacao.etapa = "CHAMANDO_ALVO"
        elif evento.status in STATUS_ATENDIDA:
            ligacao.etapa = "EM_ANDAMENTO"
            ligacao.alvo_atendeu_em = agora
            if evento.call_id:
                ligacao.provedor_call_id_alvo = evento.call_id
        elif evento.status in STATUS_FALHA:
            origem, motivo = _origem_e_motivo(evento.perna, evento.status)
            await self._falhar(ligacao, origem, motivo, agora)
        elif evento.status == StatusChamadaEnum.COMPLETED:
            if ligacao.alvo_atendeu_em is not None:
                await self._concluir(ligacao, evento.duracao_seg, agora)
            else:
                await self._falhar(ligacao, "alvo", "no-answer", agora)

    async def _e_ultima_da_acao(self, ligacao: Ligacao) -> bool:
        ultima = await self.ligacao_repo.buscar_ultima_por_acao(ligacao.acao_id)
        return ultima is not None and ultima.id == ligacao.id

    async def _concluir(self, ligacao: Ligacao, duracao_seg: int | None, agora: datetime) -> None:
        ligacao.etapa = "CONCLUIDA"
        ligacao.duracao_seg = duracao_seg
        ligacao.finalizada_em = agora

        disparo = await self.disparo_repo.buscar_por_id(ligacao.disparo_id)
        if disparo:
            disparo.status = "ENTREGUE"
            disparo.confirmado_em = agora
            await self.disparo_repo.salvar(disparo)

        if not await self._e_ultima_da_acao(ligacao):
            return
        acao = await self.acao_repo.buscar_por_id(ligacao.acao_id)
        if acao is None:
            return
        status_anterior = acao.status
        acao.status = StatusAcaoEnum.CONCLUIDA
        acao.confirmado_em = agora
        acao.proximo_passo_tipo = ProximoPassoTipoEnum.FINALIZADO
        acao.proximo_passo_instrucao = "Ligação realizada com sucesso"
        acao.proximo_passo_dados = {
            **(acao.proximo_passo_dados or {}),
            "duracao_seg": duracao_seg,
        }
        await self.acao_repo.salvar(acao)
        await incrementar_contador_se_confirmada(acao, status_anterior, self.campanha_repo)

    async def _falhar(self, ligacao: Ligacao, origem: str, motivo: str, agora: datetime) -> None:
        ligacao.etapa = "FALHA"
        ligacao.origem_falha = origem
        ligacao.motivo_falha = motivo
        ligacao.finalizada_em = agora

        disparo = await self.disparo_repo.buscar_por_id(ligacao.disparo_id)
        if disparo:
            disparo.status = "FALHA"
            disparo.proximo_passo_dados = {
                **(disparo.proximo_passo_dados or {}),
                "origem_falha": origem,
                "motivo": motivo,
            }
            await self.disparo_repo.salvar(disparo)

        if not await self._e_ultima_da_acao(ligacao):
            return
        acao = await self.acao_repo.buscar_por_id(ligacao.acao_id)
        if acao is None or acao.status == StatusAcaoEnum.CONCLUIDA:
            return
        acao.status = StatusAcaoEnum.FALHA
        acao.proximo_passo_tipo = ProximoPassoTipoEnum.FINALIZADO
        acao.proximo_passo_instrucao = "Ligação não completada; é possível tentar novamente"
        acao.proximo_passo_dados = {
            **(acao.proximo_passo_dados or {}),
            "origem_falha": origem,
            "motivo_falha": motivo,
        }
        await self.acao_repo.salvar(acao)


async def processar_evento_ligacao(
    evento: EventoLigacao, session: AsyncSession
) -> tuple[str, Ligacao]:
    return await ProcessadorEventosLigacao(session).processar(evento)
