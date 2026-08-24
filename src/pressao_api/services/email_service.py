import uuid
from typing import Any

import structlog
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    CustomArg,
    From,
    HtmlContent,
    Mail,
    MailSettings,
    ReplyTo,
    SandBoxMode,
    Subject,
    To,
)

from pressao_api.core.config import settings
from pressao_api.models.acao import Acao
from pressao_api.models.alvo import Alvo
from pressao_api.models.campanha import Campanha
from pressao_api.models.template import Template
from pressao_api.schemas.email import ResultadoEnvioEmail
from pressao_api.utils.validadores import validar_email

logger = structlog.get_logger()

CHAVES_PLACEHOLDER = {"mock-key", "test-key", "changeme", "seu-secret"}

TEMPLATE_HTML_PADRAO = """
<!DOCTYPE html>
<html lang="pt-BR">
<body style="font-family: Arial, sans-serif; color: #222; line-height: 1.5;">
  <p>Prezado(a) <strong>{alvo_nome}</strong>,</p>
  <p>
    Esta é uma mensagem de pressão da campanha
    <strong>{campanha_nome}</strong>.
  </p>
  {campanha_descricao}
  <p>{mensagem}</p>
  {assinatura}
  <hr />
  <p style="font-size: 12px; color: #666;">
    Enviado via Pressão API. ID da ação: {acao_id}
  </p>
</body>
</html>
""".strip()


class EmailService:
    """Serviço de envio de e-mails de pressão via SendGrid."""

    def __init__(self, client: SendGridAPIClient | None = None):
        self._client = client

    def _get_client(self) -> SendGridAPIClient:
        if self._client is None:
            logger.info("SENDGRID_API_KEY", api_key=settings.SENDGRID_API_KEY)
            self._client = SendGridAPIClient(settings.SENDGRID_API_KEY)
        return self._client

    def _credencial_placeholder(self) -> bool:
        chave = (settings.SENDGRID_API_KEY or "").strip().lower()
        return chave in CHAVES_PLACEHOLDER or chave.startswith("mock")

    def montar_template_pressao(
        self,
        acao: Acao,
        alvo: Alvo,
        campanha: Campanha | None = None,
        mensagem: str | None = None,
        template: Template | None = None,
    ) -> str:
        """
        Monta o HTML da pressão com dados dinâmicos.

        Com `template`, usa o conteúdo autoral da campanha; sem ele, usa o HTML padrão.
        """
        descricao = ""
        if campanha and campanha.descricao:
            descricao = f"<p>{campanha.descricao}</p>"

        assinatura = ""
        if not acao.anonimo and acao.ativista_nome:
            assinatura = f"<p>Atenciosamente,<br />{acao.ativista_nome}</p>"

        texto = mensagem or (
            "Solicitamos sua atenção e posicionamento público em relação a esta demanda."
        )

        if template is not None:
            return self._aplicar_placeholders(template.conteudo, acao, alvo, campanha)

        return TEMPLATE_HTML_PADRAO.format(
            alvo_nome=alvo.nome,
            campanha_nome=campanha.nome if campanha else "Campanha de pressão",
            campanha_descricao=descricao,
            mensagem=texto,
            assinatura=assinatura,
            acao_id=str(acao.id),
        )

    def _aplicar_placeholders(
        self,
        conteudo: str,
        acao: Acao,
        alvo: Alvo,
        campanha: Campanha | None,
    ) -> str:
        """
        Substitui os placeholders conhecidos no conteúdo do template.

        Usa `replace` em vez de `str.format` porque templates autorais contêm CSS
        inline com chaves, que o `format` interpretaria como campo de substituição.
        """
        ativista_nome = "" if acao.anonimo else (acao.ativista_nome or "")
        valores = {
            "alvo_nome": alvo.nome,
            "campanha_nome": campanha.nome if campanha else "Campanha de pressão",
            "ativista_nome": ativista_nome,
            "acao_id": str(acao.id),
        }

        html = conteudo
        for chave, valor in valores.items():
            html = html.replace("{" + chave + "}", valor)
        return html

    def enviar_pressao(
        self,
        destinatario: str,
        remetente_email: str,
        assunto: str,
        conteudo_html: str,
        acao_id: str,
        campanha_id: str | None = None,
        remetente_nome: str | None = None,
        nome_destinatario: str | None = None,
        dados_dinamicos: dict[str, Any] | None = None,
    ) -> ResultadoEnvioEmail:
        """
        Envia e-mail de pressão.

        Remetente = ativista; destinatário = alvo.

        Em sandbox (SENDGRID_SANDBOX_MODE=true):
        - habilita sandbox_mode do SendGrid no payload
        - com API key placeholder, não chama a API (dry-run local)
        - com API key real, chama a API sem entregar o e-mail
        """
        self._validar_envio(destinatario, remetente_email, assunto, conteudo_html)

        html = conteudo_html
        if dados_dinamicos is not None:
            try:
                html = conteudo_html.format(**dados_dinamicos)
            except KeyError as exc:
                raise ValueError(f"Placeholder ausente no template: {exc}") from exc

        mail = self._montar_mail(
            destinatario=destinatario,
            remetente_email=remetente_email,
            remetente_nome=remetente_nome,
            assunto=assunto,
            conteudo_html=html,
            acao_id=acao_id,
            campanha_id=campanha_id,
            nome_destinatario=nome_destinatario,
        )

        sandbox = bool(settings.SENDGRID_SANDBOX_MODE)

        if sandbox and self._credencial_placeholder():
            message_id = f"sandbox-{uuid.uuid4()}"
            logger.info(
                "E-mail de pressão em sandbox (dry-run, API não chamada)",
                acao_id=acao_id,
                destinatario=destinatario,
                remetente=remetente_email,
                message_id=message_id,
            )
            return ResultadoEnvioEmail(
                sucesso=True,
                message_id=message_id,
                sandbox=True,
                status="sandbox",
                destinatario=destinatario,
                remetente=remetente_email,
            )

        try:
            response = self._get_client().send(mail)
            status_code = getattr(response, "status_code", 0)
            if status_code not in (200, 202):
                body = getattr(response, "body", b"")
                try:
                    body_str = body.decode("utf-8")
                except UnicodeDecodeError:
                    body_str = repr(body)
                raise RuntimeError(f"SendGrid retornou HTTP {status_code}: {body_str}")

            headers = getattr(response, "headers", {}) or {}
            message_id = headers.get("X-Message-Id") or headers.get("X-Message-ID")
            if not message_id:
                message_id = str(uuid.uuid4())

            logger.info(
                "E-mail de pressão enviado",
                acao_id=acao_id,
                destinatario=destinatario,
                remetente=remetente_email,
                message_id=message_id,
                sandbox=sandbox,
                status_code=status_code,
            )
            return ResultadoEnvioEmail(
                sucesso=True,
                message_id=str(message_id),
                sandbox=sandbox,
                status="sandbox" if sandbox else "enviado",
                destinatario=destinatario,
                remetente=remetente_email,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Falha ao enviar e-mail de pressão", error=str(exc), acao_id=acao_id)
            return ResultadoEnvioEmail(
                sucesso=False,
                message_id=None,
                sandbox=sandbox,
                status="falha",
                erro=str(exc),
                destinatario=destinatario,
                remetente=remetente_email,
            )

    def _validar_envio(
        self, destinatario: str, remetente_email: str, assunto: str, conteudo_html: str
    ) -> None:
        if not destinatario or not validar_email(destinatario):
            raise ValueError("Destinatário inválido")
        if not remetente_email or not validar_email(remetente_email):
            raise ValueError("Remetente (ativista) inválido")
        if not assunto or not assunto.strip():
            raise ValueError("Assunto não pode ser vazio")
        if not conteudo_html or not conteudo_html.strip():
            raise ValueError("Conteúdo HTML não pode ser vazio")

    def _montar_mail(
        self,
        destinatario: str,
        remetente_email: str,
        remetente_nome: str | None,
        assunto: str,
        conteudo_html: str,
        acao_id: str,
        campanha_id: str | None,
        nome_destinatario: str | None,
    ) -> Mail:
        mail = Mail(
            from_email=From(remetente_email, remetente_nome or remetente_email),
            to_emails=To(destinatario, nome_destinatario),
            subject=Subject(assunto),
            html_content=HtmlContent(conteudo_html),
        )
        mail.add_custom_arg(CustomArg("acao_id", acao_id))
        if campanha_id:
            mail.add_custom_arg(CustomArg("campanha_id", campanha_id))

        mail.reply_to = ReplyTo(remetente_email, remetente_nome)

        if settings.SENDGRID_SANDBOX_MODE:
            mail.mail_settings = MailSettings(sandbox_mode=SandBoxMode(True))

        return mail


email_service = EmailService()
