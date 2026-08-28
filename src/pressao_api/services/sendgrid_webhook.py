from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from sendgrid.helpers.eventwebhook import EventWebhook, EventWebhookHeader

from pressao_api.core.config import settings
from pressao_api.repositories.acao_repository import AcaoRepository
from pressao_api.repositories.campanha_repository import CampanhaRepository
from pressao_api.repositories.disparo_repository import DisparoRepository
from pressao_api.schemas.acao import ProximoPassoTipoEnum, StatusAcaoEnum, TipoAcaoEnum
from pressao_api.services.confirmacao import incrementar_contador_se_confirmada

logger = structlog.get_logger()

HEADER_SIGNATURE = EventWebhookHeader.SIGNATURE
HEADER_TIMESTAMP = EventWebhookHeader.TIMESTAMP

EVENTOS_ENTREGA = {"delivered"}
EVENTOS_FALHA = {"bounce", "dropped", "blocked", "spamreport"}
EVENTOS_INFO = {"processed", "deferred", "open", "click", "unsubscribe", "group_unsubscribe"}


def verificar_assinatura_sendgrid(payload: bytes | str, signature: str, timestamp: str) -> bool:
    """
    Valida a assinatura ECDSA do Event Webhook do SendGrid.

    Sem chave configurada: permite em development (com warning) e rejeita em production.
    """
    chave = (settings.SENDGRID_WEBHOOK_VERIFICATION_KEY or "").strip()
    if not chave:
        if settings.APP_ENV == "production":
            logger.error("SENDGRID_WEBHOOK_VERIFICATION_KEY ausente em production")
            return False
        logger.warning("Webhook SendGrid sem chave de verificação; aceito apenas em development")
        return True

    if not signature or not timestamp:
        return False

    corpo = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    try:
        webhook = EventWebhook()
        public_key = webhook.convert_public_key_to_ecdsa(chave)
        return bool(webhook.verify_signature(corpo, signature, timestamp, public_key))
    except Exception as exc:  # noqa: BLE001
        logger.error("Falha ao verificar assinatura do webhook SendGrid", error=str(exc))
        return False


def _extrair_custom_arg(evento: dict[str, Any], chave: str) -> str | None:
    valor = evento.get(chave)
    if valor:
        return str(valor)
    unique_args = evento.get("unique_args") or evento.get("custom_args") or {}
    if isinstance(unique_args, dict):
        arg = unique_args.get(chave)
        return str(arg) if arg else None
    return None


def _extrair_acao_id(evento: dict[str, Any]) -> str | None:
    return _extrair_custom_arg(evento, "acao_id")


def _extrair_disparo_id(evento: dict[str, Any]) -> str | None:
    return _extrair_custom_arg(evento, "disparo_id")


async def _processar_evento_disparo(
    evento: dict[str, Any],
    tipo: str,
    disparo_id: UUID,
    disparo_repo: DisparoRepository,
    resumo: dict[str, int],
) -> None:
    disparo = await disparo_repo.buscar_por_id(disparo_id)
    if not disparo:
        logger.warning("Disparo não encontrado para evento SendGrid", disparo_id=str(disparo_id))
        resumo["ignorados"] += 1
        return

    dados = dict(disparo.proximo_passo_dados or {})
    dados["ultimo_evento"] = tipo
    dados["sg_message_id"] = evento.get("sg_message_id")
    dados["sg_event_id"] = evento.get("sg_event_id")

    if tipo in EVENTOS_ENTREGA:
        if disparo.status == "ENTREGUE":
            resumo["ignorados"] += 1
            return
        disparo.proximo_passo_dados = dados
        disparo.status = "ENTREGUE"
        disparo.confirmado_em = datetime.utcnow()  # noqa: DTZ003
        await disparo_repo.salvar(disparo)
        resumo["entregues"] += 1
        resumo["processados"] += 1
        logger.info("Disparo entregue", disparo_id=str(disparo_id), evento_tipo=tipo)
    elif tipo in EVENTOS_FALHA:
        if disparo.status in ("FALHA", "ERRO_ENVIO"):
            resumo["ignorados"] += 1
            return
        motivo = evento.get("reason") or evento.get("type") or tipo
        disparo.proximo_passo_dados = dados
        disparo.status = "FALHA"
        disparo.proximo_passo_dados["motivo"] = motivo
        await disparo_repo.salvar(disparo)
        resumo["falhas"] += 1
        resumo["processados"] += 1
        logger.warning(
            "Disparo falhou", disparo_id=str(disparo_id), evento_tipo=tipo, motivo=motivo
        )
    elif tipo in EVENTOS_INFO:
        disparo.proximo_passo_dados = dados
        await disparo_repo.salvar(disparo)
        resumo["processados"] += 1
        logger.info("Evento SendGrid em disparo", disparo_id=str(disparo_id), evento_tipo=tipo)
    else:
        resumo["ignorados"] += 1
        logger.info(
            "Evento SendGrid não tratado em disparo", disparo_id=str(disparo_id), evento_tipo=tipo
        )


async def processar_eventos_sendgrid(
    eventos: list[dict[str, Any]],
    repo: AcaoRepository,
    campanha_repo: CampanhaRepository | None = None,
) -> dict[str, int]:
    """Atualiza disparos ou ações simples com base nos eventos do SendGrid."""
    resumo = {"processados": 0, "entregues": 0, "falhas": 0, "ignorados": 0}
    if campanha_repo is None:
        campanha_repo = CampanhaRepository(repo.session)

    disparo_repo = DisparoRepository(repo.session)

    for evento in eventos:
        tipo = str(evento.get("event") or "").lower()

        disparo_id_raw = _extrair_disparo_id(evento)
        if disparo_id_raw:
            try:
                disparo_id = UUID(disparo_id_raw)
            except ValueError:
                logger.warning("disparo_id inválido no webhook SendGrid", disparo_id=disparo_id_raw)
                resumo["ignorados"] += 1
                continue
            await _processar_evento_disparo(evento, tipo, disparo_id, disparo_repo, resumo)
            continue

        acao_id_raw = _extrair_acao_id(evento)
        if not acao_id_raw:
            logger.warning("Evento SendGrid sem acao_id nem disparo_id", evento_tipo=tipo)
            resumo["ignorados"] += 1
            continue

        try:
            acao_id = UUID(acao_id_raw)
        except ValueError:
            logger.warning("acao_id inválido no webhook SendGrid", acao_id=acao_id_raw)
            resumo["ignorados"] += 1
            continue

        acao = await repo.buscar_por_id(acao_id)
        if not acao:
            logger.warning("Ação não encontrada para evento SendGrid", acao_id=acao_id_raw)
            resumo["ignorados"] += 1
            continue

        if acao.tipo_acao == TipoAcaoEnum.MULTI_ALVO.value:
            logger.info(
                "Evento SendGrid ignorado para ação multi_alvo (use disparo_id)",
                acao_id=acao_id_raw,
                evento_tipo=tipo,
            )
            resumo["ignorados"] += 1
            continue

        dados = dict(acao.proximo_passo_dados or {})
        dados["ultimo_evento"] = tipo
        dados["sg_message_id"] = evento.get("sg_message_id")
        dados["sg_event_id"] = evento.get("sg_event_id")

        if tipo in EVENTOS_ENTREGA:
            if acao.status != StatusAcaoEnum.PROCESSANDO:
                resumo["ignorados"] += 1
                continue
            status_anterior = acao.status
            acao.proximo_passo_dados = dados
            acao.status = StatusAcaoEnum.CONCLUIDA
            acao.confirmado_em = datetime.utcnow()  # noqa: DTZ003
            acao.proximo_passo_tipo = ProximoPassoTipoEnum.FINALIZADO
            acao.proximo_passo_instrucao = "E-mail entregue com sucesso"
            await repo.salvar(acao)
            await incrementar_contador_se_confirmada(acao, status_anterior, campanha_repo)
            resumo["entregues"] += 1
            resumo["processados"] += 1
            logger.info("E-mail entregue", acao_id=acao_id_raw, evento_tipo=tipo)
        elif tipo in EVENTOS_FALHA:
            if acao.status not in (StatusAcaoEnum.PROCESSANDO, StatusAcaoEnum.CONCLUIDA):
                resumo["ignorados"] += 1
                continue
            motivo = evento.get("reason") or evento.get("type") or tipo
            acao.proximo_passo_dados = dados
            acao.status = StatusAcaoEnum.FALHA
            acao.proximo_passo_tipo = ProximoPassoTipoEnum.FINALIZADO
            acao.proximo_passo_instrucao = f"Falha no envio: {motivo}"
            await repo.salvar(acao)
            resumo["falhas"] += 1
            resumo["processados"] += 1
            logger.warning("E-mail falhou", acao_id=acao_id_raw, evento_tipo=tipo, motivo=motivo)
        elif tipo in EVENTOS_INFO:
            acao.proximo_passo_dados = dados
            await repo.salvar(acao)
            resumo["processados"] += 1
            logger.info("Evento SendGrid informado", acao_id=acao_id_raw, evento_tipo=tipo)
        else:
            resumo["ignorados"] += 1
            logger.info("Evento SendGrid não tratado", acao_id=acao_id_raw, evento_tipo=tipo)

    return resumo
