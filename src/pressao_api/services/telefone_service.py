import uuid
from typing import Any

import structlog
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from pressao_api.core.config import settings
from pressao_api.schemas.telefone import ResultadoLigacao
from pressao_api.services.templates import aplicar_placeholders
from pressao_api.services.twilio_voz import EVENTOS_STATUS, url_publica
from pressao_api.utils.validadores import validar_telefone

logger = structlog.get_logger()

CHAVES_PLACEHOLDER = {"mock-sid", "mock-token", "test-sid", "test-token", "changeme"}

ROTEIRO_PADRAO = (
    "Olá, meu nome é {ativista_nome}. Estou ligando para pedir que {alvo_nome} "
    "apoie a campanha {campanha_nome}. Essa decisão é muito importante. "
    "Contamos com o apoio de vocês!"
)


class TelefoneService:
    """Serviço de ligações de pressão: liga para o ativista e o conecta ao alvo."""

    @staticmethod
    def _placeholder(valor: str | None) -> bool:
        chave = (valor or "").strip().lower()
        return not chave or chave in CHAVES_PLACEHOLDER or chave.startswith("mock")

    def _usa_api_key(self) -> bool:
        return bool((settings.TWILIO_API_KEY_SID or "").strip())

    def _credencial_placeholder(self) -> bool:
        if self._placeholder(settings.TWILIO_ACCOUNT_SID):
            return True
        if self._usa_api_key():
            return self._placeholder(settings.TWILIO_API_KEY_SID) or self._placeholder(
                settings.TWILIO_API_KEY_SECRET
            )
        return self._placeholder(settings.TWILIO_AUTH_TOKEN)

    def _cliente(self) -> Client:
        if self._usa_api_key():
            return Client(
                settings.TWILIO_API_KEY_SID,
                settings.TWILIO_API_KEY_SECRET,
                settings.TWILIO_ACCOUNT_SID,
            )
        return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    def modo_dry_run(self) -> bool:
        return bool(settings.TWILIO_SANDBOX_MODE) or self._credencial_placeholder()

    def montar_roteiro(self, acao: Any, alvo: Any, campanha: Any, template: Any) -> str:
        texto = template.conteudo if template else ROTEIRO_PADRAO
        ativista_nome = "" if acao.anonimo else (acao.ativista_nome or "")
        return aplicar_placeholders(
            texto,
            {
                "alvo_nome": alvo.nome if alvo else "",
                "campanha_nome": campanha.nome if campanha else "Campanha de pressão",
                "ativista_nome": ativista_nome or "[seu nome]",
                "acao_id": str(acao.id),
            },
        )

    def iniciar_ligacao(
        self,
        telefone_origem: str | None,
        telefone_ativista: str,
        telefone_alvo: str,
        ligacao_id: str,
        acao_id: str,
        campanha_id: str,
    ) -> ResultadoLigacao:
        """
        Pede ao provedor a ligação para o ativista, que será conectada ao alvo.

        Em dry-run (TWILIO_SANDBOX_MODE=true ou credenciais placeholder) nenhuma chamada é
        feita; o andamento chega pelo webhook de simulação.
        """
        if not validar_telefone(telefone_ativista):
            raise ValueError("Telefone do ativista inválido")
        if not validar_telefone(telefone_alvo):
            raise ValueError("Telefone do alvo inválido")

        if self.modo_dry_run():
            call_id = f"dryrun-{uuid.uuid4()}"
            logger.info(
                "Ligação de pressão em dry-run (provedor não chamado)",
                ligacao_id=ligacao_id,
                acao_id=acao_id,
                campanha_id=campanha_id,
                call_id=call_id,
            )
            return ResultadoLigacao(sucesso=True, call_id=call_id, dry_run=True, provedor="dry_run")

        if not settings.TWILIO_WEBHOOK_URL.startswith("https://"):
            erro = "TWILIO_WEBHOOK_URL precisa ser a URL pública https da API"
            logger.error(erro, ligacao_id=ligacao_id, acao_id=acao_id)
            return ResultadoLigacao(sucesso=False, provedor="twilio", erro=erro)

        try:
            chamada = self._cliente().calls.create(
                to=telefone_ativista,
                from_=telefone_origem,
                url=url_publica(f"/twiml/{ligacao_id}"),
                method="POST",
                status_callback=url_publica(f"/status/{ligacao_id}/ativista"),
                status_callback_event=EVENTOS_STATUS,
                status_callback_method="POST",
                timeout=settings.TELEFONE_TIMEOUT_TOQUE_SEG,
            )
        except TwilioRestException as exc:
            erro = f"Twilio {exc.code}: {exc.msg}"
            logger.error(
                "Twilio recusou a ligação", ligacao_id=ligacao_id, acao_id=acao_id, erro=erro
            )
            return ResultadoLigacao(sucesso=False, provedor="twilio", erro=erro)

        logger.info(
            "Ligação de pressão pedida ao Twilio",
            ligacao_id=ligacao_id,
            acao_id=acao_id,
            campanha_id=campanha_id,
            call_id=chamada.sid,
        )
        return ResultadoLigacao(sucesso=True, call_id=chamada.sid, provedor="twilio")


telefone_service = TelefoneService()
