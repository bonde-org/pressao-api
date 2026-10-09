import json
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from pressao_api.core.config import settings
from pressao_api.core.database import get_db
from pressao_api.models.ligacao import ETAPAS_TERMINAIS, Ligacao
from pressao_api.repositories.acao_repository import AcaoRepository
from pressao_api.repositories.alvo_repository import AlvoRepository
from pressao_api.repositories.campanha_repository import CampanhaRepository
from pressao_api.repositories.ligacao_repository import LigacaoRepository
from pressao_api.schemas.telefone import EventoLigacao, PernaLigacaoEnum, StatusChamadaEnum
from pressao_api.services.ligacao_eventos import (
    LigacaoNaoEncontradaError,
    processar_evento_ligacao,
)
from pressao_api.services.sendgrid_webhook import (
    HEADER_SIGNATURE,
    HEADER_TIMESTAMP,
    processar_eventos_sendgrid,
    verificar_assinatura_sendgrid,
)
from pressao_api.services.twilio_voz import (
    HEADER_ASSINATURA,
    MENSAGEM_SEM_CONFIRMACAO,
    assinatura_valida,
    evento_do_callback,
    twiml_conectar,
    twiml_confirmacao,
    twiml_encerrar,
    url_publica,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

TWILIO_ROTA = "/twilio"
TWILIO_PREFIXO = f"/webhooks{TWILIO_ROTA}"


@router.post("/sendgrid", status_code=status.HTTP_200_OK, summary="Webhook de eventos SendGrid")
async def webhook_sendgrid(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Recebe eventos do Event Webhook do SendGrid (delivery, bounce, open, click, etc.).

    Autenticação: assinatura ECDSA (não usa JWT).
    """
    payload = await request.body()
    signature = request.headers.get(HEADER_SIGNATURE, "")
    timestamp = request.headers.get(HEADER_TIMESTAMP, "")

    if not verificar_assinatura_sendgrid(payload, signature, timestamp):
        raise HTTPException(status_code=401, detail="Assinatura do webhook SendGrid inválida")

    try:
        eventos = json.loads(payload.decode("utf-8") if payload else "[]")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Payload JSON inválido") from exc

    if not isinstance(eventos, list):
        raise HTTPException(status_code=400, detail="Payload deve ser uma lista de eventos")

    repo = AcaoRepository(db)
    campanha_repo = CampanhaRepository(db)
    resumo = await processar_eventos_sendgrid(eventos, repo, campanha_repo)
    logger.info("Webhook SendGrid processado", **resumo)
    return {"status": "ok", **resumo}


@router.post(
    "/telefone/simular",
    status_code=status.HTTP_200_OK,
    summary="Simula evento de ligação (fora de produção)",
)
async def webhook_telefone_simular(evento: EventoLigacao, db: AsyncSession = Depends(get_db)):
    """
    Aplica um evento de ligação no formato interno, como o webhook do provedor fará.

    Serve para desenvolvimento, testes e homologação com o provedor em dry-run.
    Indisponível em produção.
    """
    if settings.APP_ENV == "production":
        raise HTTPException(status_code=404, detail="Not Found")

    try:
        resultado, ligacao = await processar_evento_ligacao(evento, db)
    except LigacaoNaoEncontradaError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"status": "ok", "resultado": resultado, "etapa": ligacao.etapa}


async def _form_twilio_assinado(request: Request) -> dict[str, str]:
    """Lê o form do Twilio e valida a assinatura sobre a URL pública (não `request.url`)."""
    params = {chave: str(valor) for chave, valor in (await request.form()).items()}
    sufixo = request.url.path.split(TWILIO_PREFIXO, 1)[-1]
    if request.url.query:
        sufixo = f"{sufixo}?{request.url.query}"
    assinatura = request.headers.get(HEADER_ASSINATURA, "")
    if not assinatura_valida(url_publica(sufixo), params, assinatura):
        logger.warning("Assinatura do webhook Twilio inválida", caminho=request.url.path)
        raise HTTPException(status_code=403, detail="Assinatura do webhook Twilio inválida")
    return params


def _xml(conteudo: str) -> Response:
    return Response(content=conteudo, media_type="application/xml")


async def _ligacao_ativa(db: AsyncSession, ligacao_id: UUID) -> Ligacao | None:
    ligacao = await LigacaoRepository(db).buscar_por_id(ligacao_id)
    if ligacao is None or ligacao.etapa in ETAPAS_TERMINAIS:
        return None
    return ligacao


@router.post(f"{TWILIO_ROTA}/twiml/{{ligacao_id}}", summary="TwiML da perna do ativista (Twilio)")
async def webhook_twilio_twiml(
    ligacao_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
):
    """Ativista atendeu: pede "pressione 1" antes de ligar para o alvo (protege contra caixa postal)."""
    await _form_twilio_assinado(request)
    ligacao = await _ligacao_ativa(db, ligacao_id)
    if ligacao is None:
        return _xml(twiml_encerrar())

    alvo = await AlvoRepository(db).buscar_por_id(ligacao.alvo_id)
    acao = await AcaoRepository(db).buscar_por_id(ligacao.acao_id)
    campanha = await CampanhaRepository(db).buscar_por_id(acao.campanha_id) if acao else None
    return _xml(
        twiml_confirmacao(
            str(ligacao.id),
            campanha.nome if campanha else "de pressão",
            alvo.nome if alvo else "o alvo da campanha",
        )
    )


@router.post(f"{TWILIO_ROTA}/conectar/{{ligacao_id}}", summary="Resposta do 'pressione 1' (Twilio)")
async def webhook_twilio_conectar(
    ligacao_id: UUID, request: Request, db: AsyncSession = Depends(get_db)
):
    """Com `Digits=1` disca para o alvo; sem confirmação, registra falha do ativista e desliga."""
    params = await _form_twilio_assinado(request)
    ligacao = await _ligacao_ativa(db, ligacao_id)
    if ligacao is None:
        return _xml(twiml_encerrar())

    if params.get("Digits") != "1":
        evento = EventoLigacao(
            ligacao_id=ligacao.id,
            perna=PernaLigacaoEnum.ATIVISTA,
            status=StatusChamadaEnum.NO_ANSWER,
            call_id=params.get("CallSid") or None,
        )
        await processar_evento_ligacao(evento, db)
        return _xml(twiml_encerrar(MENSAGEM_SEM_CONFIRMACAO))

    alvo = await AlvoRepository(db).buscar_por_id(ligacao.alvo_id)
    acao = await AcaoRepository(db).buscar_por_id(ligacao.acao_id)
    campanha = await CampanhaRepository(db).buscar_por_id(acao.campanha_id) if acao else None
    if campanha is None or not campanha.telefone_origem:
        logger.error("Ligação sem número de origem na campanha", ligacao_id=str(ligacao.id))
        return _xml(twiml_encerrar())
    return _xml(
        twiml_conectar(
            str(ligacao.id),
            campanha.telefone_origem,
            ligacao.telefone_alvo,
            alvo.nome if alvo else "o alvo da campanha",
        )
    )


@router.post(
    f"{TWILIO_ROTA}/status/{{ligacao_id}}/{{perna}}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Status de uma perna da ligação (Twilio)",
)
async def webhook_twilio_status(
    ligacao_id: UUID,
    perna: PernaLigacaoEnum,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Converte `CallStatus` em `EventoLigacao`. Sempre 204 para o Twilio não repetir o envio."""
    params = await _form_twilio_assinado(request)
    evento = evento_do_callback(ligacao_id, perna, params)
    if evento is None:
        logger.info(
            "Status Twilio ignorado", ligacao_id=str(ligacao_id), status=params.get("CallStatus")
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    try:
        await processar_evento_ligacao(evento, db)
    except LigacaoNaoEncontradaError:
        logger.warning("Status Twilio de ligação inexistente", ligacao_id=str(ligacao_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
