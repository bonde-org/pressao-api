from collections.abc import Mapping
from uuid import UUID

import structlog
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import Dial, Gather, VoiceResponse

from pressao_api.core.config import settings
from pressao_api.schemas.telefone import EventoLigacao, PernaLigacaoEnum, StatusChamadaEnum

logger = structlog.get_logger()

HEADER_ASSINATURA = "X-Twilio-Signature"
IDIOMA = "pt-BR"
VOZ = "Polly.Camila"
TIMEOUT_DIGITO_SEG = 10
PAUSA_AO_ATENDER_SEG = 1
PAUSA_ENTRE_MENSAGENS_SEG = 5
EVENTOS_STATUS = ["initiated", "ringing", "answered", "completed"]
TOKENS_PLACEHOLDER = {"", "mock-token", "test-token", "changeme"}

MENSAGEM_SEM_CONFIRMACAO = (
    "Não recebemos a sua confirmação. Você pode tentar de novo pelo site. Até logo!"
)


def url_publica(sufixo: str) -> str:
    return settings.TWILIO_WEBHOOK_URL.rstrip("/") + sufixo


def assinatura_valida(url: str, params: Mapping[str, str], assinatura: str) -> bool:
    """
    Valida `X-Twilio-Signature` com o Auth Token sobre a URL pública configurada.

    Sem Auth Token real: aceita fora de produção (dev/simulação) e recusa em produção.
    """
    token = (settings.TWILIO_AUTH_TOKEN or "").strip()
    if token.lower() in TOKENS_PLACEHOLDER or token.lower().startswith("mock"):
        if settings.APP_ENV == "production":
            logger.error("Webhook Twilio recusado: TWILIO_AUTH_TOKEN não configurado em produção")
            return False
        logger.warning("Webhook Twilio sem validação de assinatura (Auth Token não configurado)")
        return True
    if not assinatura:
        return False
    return bool(RequestValidator(token).validate(url, dict(params), assinatura))


def _say(resposta: VoiceResponse | Gather, texto: str) -> None:
    resposta.say(texto, language=IDIOMA, voice=VOZ)


def twiml_confirmacao(ligacao_id: str, campanha_nome: str, alvo_nome: str) -> str:
    resposta = VoiceResponse()
    gather = Gather(
        num_digits=1,
        timeout=TIMEOUT_DIGITO_SEG,
        action=url_publica(f"/conectar/{ligacao_id}"),
        method="POST",
        action_on_empty_result=True,
    )
    instrucao = f"Para ligar agora para {alvo_nome}, pressione 1."
    gather.pause(length=PAUSA_AO_ATENDER_SEG)
    _say(gather, f"Olá! Aqui é da campanha {campanha_nome}. {instrucao}")
    gather.pause(length=PAUSA_ENTRE_MENSAGENS_SEG)
    _say(gather, instrucao)
    resposta.append(gather)
    return str(resposta)


def twiml_conectar(
    ligacao_id: str, telefone_origem: str, telefone_alvo: str, alvo_nome: str
) -> str:
    resposta = VoiceResponse()
    _say(resposta, f"Conectando com {alvo_nome}. Boa conversa!")
    dial = Dial(caller_id=telefone_origem, timeout=settings.TELEFONE_TIMEOUT_TOQUE_SEG)
    dial.number(
        telefone_alvo,
        status_callback=url_publica(f"/status/{ligacao_id}/alvo"),
        status_callback_event=" ".join(EVENTOS_STATUS),
        status_callback_method="POST",
    )
    resposta.append(dial)
    return str(resposta)


def twiml_encerrar(mensagem: str | None = None) -> str:
    resposta = VoiceResponse()
    if mensagem:
        _say(resposta, mensagem)
    resposta.hangup()
    return str(resposta)


def evento_do_callback(
    ligacao_id: UUID, perna: PernaLigacaoEnum, params: Mapping[str, str]
) -> EventoLigacao | None:
    try:
        status = StatusChamadaEnum(params.get("CallStatus", ""))
    except ValueError:
        return None
    duracao = params.get("CallDuration")
    return EventoLigacao(
        ligacao_id=ligacao_id,
        perna=perna,
        status=status,
        duracao_seg=int(duracao) if duracao and duracao.isdigit() else None,
        call_id=params.get("CallSid") or None,
    )
