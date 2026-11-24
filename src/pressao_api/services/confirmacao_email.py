"""E-mail de confirmação enviado ao ativista depois da primeira ação na campanha."""

import asyncio
import html
import re

import structlog

from pressao_api.schemas.campanha import ConfirmacaoEmailConfig
from pressao_api.services.email_service import email_service

logger = structlog.get_logger()

_URL = re.compile(r"(?P<url>(?:https?://|www\.)[^\s<]+)")


def _primeiro_nome(nome: str | None) -> str:
    partes = (nome or "").split()
    return partes[0] if partes else ""


def _linkificar(texto_escapado: str) -> str:
    def trocar(m: re.Match) -> str:
        url = m.group("url").rstrip(".,;:!?)")
        resto = m.group("url")[len(url) :]
        href = url if url.startswith("http") else f"https://{url}"
        return f'<a href="{href}">{url}</a>{resto}'

    return _URL.sub(trocar, texto_escapado)


def montar_texto(cfg: ConfirmacaoEmailConfig, nome: str | None) -> str:
    return cfg.texto.replace("{nome}", _primeiro_nome(nome)).strip()


def montar_html(cfg: ConfirmacaoEmailConfig, nome: str | None) -> str:
    """Texto puro → HTML simples: parágrafos por linha em branco, <br> nas quebras, links ativos."""
    paragrafos = [p for p in re.split(r"\n\s*\n", montar_texto(cfg, nome)) if p.strip()]
    corpo = "".join(
        '<p style="margin:0 0 16px">'
        + _linkificar(html.escape(p.strip())).replace("\n", "<br />")
        + "</p>"
        for p in paragrafos
    )
    return (
        '<!DOCTYPE html><html lang="pt-BR"><body style="font-family:Arial,sans-serif;'
        f'color:#222;line-height:1.5;font-size:16px">{corpo}</body></html>'
    )


async def enviar_confirmacao(
    cfg: ConfirmacaoEmailConfig, *, nome: str | None, email: str, campanha_id: str
) -> bool:
    """Envia o e-mail (SendGrid é síncrono: roda em thread). Nunca levanta exceção."""
    try:
        resultado = await asyncio.to_thread(
            email_service.enviar_transacional,
            destinatario=email,
            remetente_email=cfg.remetente_email,
            remetente_nome=cfg.remetente_nome,
            assunto=cfg.assunto,
            conteudo_html=montar_html(cfg, nome),
            conteudo_texto=montar_texto(cfg, nome),
            campanha_id=campanha_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Falha ao enviar e-mail de confirmação", erro=type(exc).__name__)
        return False
    if not resultado.sucesso:
        logger.error("Falha ao enviar e-mail de confirmação", erro=resultado.erro)
    return bool(resultado.sucesso)
