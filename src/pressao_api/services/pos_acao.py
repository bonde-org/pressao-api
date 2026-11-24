"""Pós-ação da campanha: e-mail de confirmação ao ativista e contato no Action Network.

Roda em background depois da resposta (o ativista não espera nem é afetado por falhas aqui).
Não usa a sessão do banco da requisição, que já está fechada quando a tarefa executa.
"""

import asyncio
from dataclasses import dataclass

import structlog
from fastapi import BackgroundTasks

from pressao_api.models.acao import Acao
from pressao_api.models.campanha import Campanha
from pressao_api.repositories.acao_repository import AcaoRepository
from pressao_api.schemas.campanha import PosAcaoConfig
from pressao_api.services import actionnetwork
from pressao_api.services.confirmacao_email import enviar_confirmacao
from pressao_api.utils.validadores import validar_email

logger = structlog.get_logger()


@dataclass(frozen=True)
class PosAcaoJob:
    campanha_id: str
    config: PosAcaoConfig
    nome: str | None
    email: str
    telefone: str | None
    enviar_confirmacao: bool


def montar_job(acao: Acao, campanha: Campanha | None, *, primeira_acao: bool) -> PosAcaoJob | None:
    """Decide se esta ação dispara o pós-ação. None = nada a fazer."""
    if campanha is None or not campanha.pos_acao:
        return None
    try:
        config = PosAcaoConfig.model_validate(campanha.pos_acao)
    except ValueError:
        logger.error("pos_acao inválido na campanha", campanha_id=str(campanha.id))
        return None
    if acao.canal not in config.canais or acao.anonimo:
        return None
    email = (acao.ativista_email or "").strip()
    if not validar_email(email):
        return None
    return PosAcaoJob(
        campanha_id=str(campanha.id),
        config=config,
        nome=acao.ativista_nome,
        email=email,
        telefone=acao.ativista_telefone,
        # Confirmação só na primeira ação do ativista na campanha (não a cada envio)
        enviar_confirmacao=bool(config.confirmacao_email) and primeira_acao,
    )


async def executar(job: PosAcaoJob) -> None:
    """Executa os passos em paralelo; cada um isolado, falha de um não afeta o outro."""
    tarefas = []
    if job.config.actionnetwork and actionnetwork.integracao_ativa():
        tarefas.append(
            actionnetwork.registrar_contato(
                nome=job.nome,
                email=job.email,
                telefone=job.telefone,
                tags=job.config.actionnetwork.tags,
            )
        )
    if job.enviar_confirmacao and job.config.confirmacao_email:
        tarefas.append(
            enviar_confirmacao(
                job.config.confirmacao_email,
                nome=job.nome,
                email=job.email,
                campanha_id=job.campanha_id,
            )
        )
    if tarefas:
        await asyncio.gather(*tarefas, return_exceptions=True)


async def agendar_pos_acao(
    background_tasks: BackgroundTasks,
    acao: Acao,
    campanha: Campanha | None,
    repo: AcaoRepository,
) -> bool:
    """Chamar com a ação já CONCLUIDA e a sessão aberta. Devolve True se agendou."""
    if campanha is None or not campanha.pos_acao or not acao.ativista_email:
        return False
    try:
        total = await repo.contar_concluidas_por_email(acao.campanha_id, acao.ativista_email)
        job = montar_job(acao, campanha, primeira_acao=total <= 1)
    except Exception as exc:  # noqa: BLE001
        logger.error("Falha ao preparar pós-ação", erro=type(exc).__name__)
        return False
    if job is None:
        return False
    background_tasks.add_task(executar, job)
    return True
