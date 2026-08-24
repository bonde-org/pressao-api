import structlog

from pressao_api.core.config import settings
from pressao_api.models.acao import Acao
from pressao_api.models.alvo import Alvo
from pressao_api.models.campanha import Campanha
from pressao_api.models.template import Template
from pressao_api.schemas.acao import CanalEnum, ProximoPassoTipoEnum, StatusAcaoEnum
from pressao_api.services.email_service import email_service

logger = structlog.get_logger()


class OrquestradorCanais:
    """Orquestrador de canais para ações de pressão."""

    def __init__(self):
        # Mapeamento de estratégias por canal
        self.estrategias = {
            CanalEnum.EMAIL: self._estrategia_email,
            CanalEnum.TELEFONE: self._estrategia_telefone,
            CanalEnum.WHATSAPP: self._estrategia_whatsapp,
            CanalEnum.INSTAGRAM: self._estrategia_instagram,
        }

    async def executar(
        self,
        acao: Acao,
        alvo: Alvo | None = None,
        campanha: Campanha | None = None,
        template: Template | None = None,
    ) -> Acao:
        """Executa a estratégia do canal."""
        try:
            canal = CanalEnum(acao.canal)
            estrategia = self.estrategias.get(canal)

            if not estrategia:
                raise ValueError(f"Canal não suportado: {acao.canal}")

            logger.info("Executando ação", acao_id=str(acao.id), canal=acao.canal)

            await estrategia(acao, alvo=alvo, campanha=campanha, template=template)

            return acao

        except Exception as e:
            logger.error("Erro ao executar ação", error=str(e), acao_id=str(acao.id))
            acao.status = StatusAcaoEnum.FALHA
            raise

    async def _estrategia_email(
        self,
        acao: Acao,
        alvo: Alvo | None = None,
        campanha: Campanha | None = None,
        template: Template | None = None,
    ):
        """Estratégia para Email (SendGrid). Remetente = ativista; destinatário = alvo."""
        if alvo is None or not alvo.contato:
            raise ValueError("Alvo com e-mail é obrigatório para o canal email")

        remetente_email = acao.ativista_email
        remetente_nome = acao.ativista_nome
        if not remetente_email:
            raise ValueError("Canal email exige e-mail do ativista como remetente")

        html = email_service.montar_template_pressao(
            acao=acao, alvo=alvo, campanha=campanha, template=template
        )
        if template:
            assunto = template.titulo
        else:
            assunto = f"Pressão: {campanha.nome}" if campanha else "Mensagem de pressão"
        resultado = email_service.enviar_pressao(
            destinatario=alvo.contato,
            remetente_email=remetente_email,
            remetente_nome=remetente_nome,
            assunto=assunto,
            conteudo_html=html,
            acao_id=str(acao.id),
            campanha_id=str(acao.campanha_id),
            nome_destinatario=alvo.nome,
        )

        if not resultado.sucesso:
            raise RuntimeError(resultado.erro or "Falha ao enviar e-mail via SendGrid")

        acao.status = StatusAcaoEnum.PROCESSANDO
        acao.proximo_passo_tipo = ProximoPassoTipoEnum.WEBHOOK_AGUARDAR
        acao.proximo_passo_instrucao = "Aguardando confirmação de entrega via webhook"
        acao.proximo_passo_dados = {
            "provider": "sendgrid",
            "message_id": resultado.message_id,
            "sandbox": resultado.sandbox,
            "destinatario": alvo.contato,
            "remetente": remetente_email,
            "evento": "delivered",
            "webhook_url": settings.SENDGRID_WEBHOOK_URL,
            "template_id": str(acao.template_id) if acao.template_id else None,
        }
        logger.info(
            "Email enviado",
            acao_id=str(acao.id),
            message_id=resultado.message_id,
            sandbox=resultado.sandbox,
            template_id=str(acao.template_id) if acao.template_id else None,
        )

    async def _estrategia_telefone(
        self,
        acao: Acao,
        alvo: Alvo | None = None,
        campanha: Campanha | None = None,
        template: Template | None = None,
    ):
        """Estratégia para Telefone (Twilio)."""
        acao.status = StatusAcaoEnum.PROCESSANDO
        acao.proximo_passo_tipo = ProximoPassoTipoEnum.WEBHOOK_AGUARDAR
        acao.proximo_passo_instrucao = "Aguardando confirmação de chamada via webhook"
        acao.proximo_passo_dados = {
            "webhook_url": "https://api.twilio.com/v3/webhook",
            "evento": "call_completed",
        }
        logger.info("Chamada telefônica iniciada", acao_id=str(acao.id))

    async def _estrategia_whatsapp(
        self,
        acao: Acao,
        alvo: Alvo | None = None,
        campanha: Campanha | None = None,
        template: Template | None = None,
    ):
        """Estratégia para WhatsApp (Manual)."""
        acao.status = StatusAcaoEnum.AGUARDANDO_ACAO_HUMANA
        acao.proximo_passo_tipo = ProximoPassoTipoEnum.REDIRECIONAR_LINK
        acao.proximo_passo_instrucao = "Clique no link para enviar a mensagem no WhatsApp"
        acao.proximo_passo_dados = {
            "link": "https://wa.me/5511999999999?text=Ol%C3%A1%2C%20esta%20%C3%A9%20uma%20mensagem%20de%20press%C3%A3o",
            "texto": "Olá, esta é uma mensagem de pressão sobre o tema X",
        }
        logger.info("Link WhatsApp gerado", acao_id=str(acao.id))

    async def _estrategia_instagram(
        self,
        acao: Acao,
        alvo: Alvo | None = None,
        campanha: Campanha | None = None,
        template: Template | None = None,
    ):
        """Estratégia para Instagram (Manual)."""
        acao.status = StatusAcaoEnum.AGUARDANDO_ACAO_HUMANA
        acao.proximo_passo_tipo = ProximoPassoTipoEnum.EXIBIR_TEXTO_E_ABRIR_PERFIL
        acao.proximo_passo_instrucao = "Copie o texto e envie no perfil do Instagram"
        acao.proximo_passo_dados = {
            "perfil": "@alvo_instagram",
            "texto": "Olá, esta é uma mensagem de pressão sobre o tema X. Por favor, considere nossa demanda.",
            "url_perfil": "https://instagram.com/alvo_instagram",
        }
        logger.info("Texto Instagram gerado", acao_id=str(acao.id))


orquestrador = OrquestradorCanais()
