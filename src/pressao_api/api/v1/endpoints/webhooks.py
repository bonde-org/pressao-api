import json

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from pressao_api.core.database import get_db
from pressao_api.repositories.acao_repository import AcaoRepository
from pressao_api.services.sendgrid_webhook import (
    HEADER_SIGNATURE,
    HEADER_TIMESTAMP,
    processar_eventos_sendgrid,
    verificar_assinatura_sendgrid,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


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
    resumo = await processar_eventos_sendgrid(eventos, repo)
    logger.info("Webhook SendGrid processado", **resumo)
    return {"status": "ok", **resumo}
