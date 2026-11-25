"""E-mail de confirmação enviado ao ativista depois da primeira ação na campanha."""

import asyncio
import html
import re
from urllib.parse import quote

import structlog

from pressao_api.schemas.campanha import ConfirmacaoEmailConfig
from pressao_api.services.email_service import email_service

logger = structlog.get_logger()

# Marcador do botão no texto: {botao} ou [COMPARTILHE]. Sem marcador, o botão vai no fim.
_MARCADOR = re.compile(r"\{botao\}|\[compartilhe\]", re.IGNORECASE)

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


def link_whatsapp(cfg: ConfirmacaoEmailConfig) -> str | None:
    """Link que abre o WhatsApp com a mensagem de compartilhamento já escrita."""
    if not cfg.botao_whatsapp:
        return None
    return f"https://wa.me/?text={quote(cfg.botao_whatsapp, safe='')}"


def montar_texto(cfg: ConfirmacaoEmailConfig, nome: str | None) -> str:
    texto = cfg.texto.replace("{nome}", _primeiro_nome(nome)).strip()
    link = link_whatsapp(cfg)
    if not link:
        return _MARCADOR.sub("", texto).strip()
    linha = f"{cfg.botao_texto}: {link}"
    if _MARCADOR.search(texto):
        return _MARCADOR.sub(linha, texto)
    return f"{texto}\n\n{linha}"


def montar_html(cfg: ConfirmacaoEmailConfig, nome: str | None) -> str:
    """Texto puro → HTML simples: parágrafos por linha em branco, <br> nas quebras, links ativos."""
    texto = cfg.texto.replace("{nome}", _primeiro_nome(nome)).strip()
    link = link_whatsapp(cfg)
    botao = ""
    if link:
        botao = (
            '<p style="margin:24px 0"><a href="'
            + html.escape(link, quote=True)
            + '" style="display:inline-block;background:#25D366;color:#fff;font-weight:bold;'
            'text-decoration:none;padding:14px 28px;border-radius:6px">'
            + html.escape(cfg.botao_texto)
            + "</a></p>"
        )
    tem_marcador = bool(_MARCADOR.search(texto))
    partes: list[str] = []
    for p in re.split(r"\n\s*\n", texto):
        if not p.strip():
            continue
        if _MARCADOR.fullmatch(p.strip()):
            partes.append(botao)
            continue
        p = _MARCADOR.sub("", p).strip()
        if p:
            partes.append(
                '<p style="margin:0 0 16px">'
                + _linkificar(html.escape(p)).replace("\n", "<br />")
                + "</p>"
            )
    corpo = "".join(partes)
    if botao and not tem_marcador:
        corpo += botao
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
