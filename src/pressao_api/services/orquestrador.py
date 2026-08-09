import structlog

from pressao_api.models.acao import Acao
from pressao_api.schemas.acao import CanalEnum, ProximoPassoTipoEnum, StatusAcaoEnum

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
    
    async def executar(self, acao: Acao) -> Acao:
        """Executa a estratégia do canal."""
        try:
            canal = CanalEnum(acao.canal)
            estrategia = self.estrategias.get(canal)
            
            if not estrategia:
                raise ValueError(f"Canal não suportado: {acao.canal}")
            
            logger.info(
                "Executando ação",
                acao_id=str(acao.id),
                canal=acao.canal
            )
            
            # Executa a estratégia
            await estrategia(acao)
            
            return acao
            
        except Exception as e:
            logger.error("Erro ao executar ação", error=str(e), acao_id=str(acao.id))
            acao.status = StatusAcaoEnum.FALHA
            raise
    
    async def _estrategia_email(self, acao: Acao):
        """Estratégia para Email (SendGrid)."""
        # Mock: simula envio de email
        acao.status = StatusAcaoEnum.PROCESSANDO
        acao.proximo_passo_tipo = ProximoPassoTipoEnum.WEBHOOK_AGUARDAR
        acao.proximo_passo_instrucao = "Aguardando confirmação de entrega via webhook"
        acao.proximo_passo_dados = {
            "webhook_url": "https://api.sendgrid.com/v3/webhook",
            "evento": "email_delivered"
        }
        logger.info("Email enviado", acao_id=str(acao.id))
    
    async def _estrategia_telefone(self, acao: Acao):
        """Estratégia para Telefone (Twilio)."""
        # Mock: simula chamada telefônica
        acao.status = StatusAcaoEnum.PROCESSANDO
        acao.proximo_passo_tipo = ProximoPassoTipoEnum.WEBHOOK_AGUARDAR
        acao.proximo_passo_instrucao = "Aguardando confirmação de chamada via webhook"
        acao.proximo_passo_dados = {
            "webhook_url": "https://api.twilio.com/v3/webhook",
            "evento": "call_completed"
        }
        logger.info("Chamada telefônica iniciada", acao_id=str(acao.id))
    
    async def _estrategia_whatsapp(self, acao: Acao):
        """Estratégia para WhatsApp (Manual)."""
        # Mock: gera link para manual
        acao.status = StatusAcaoEnum.AGUARDANDO_ACAO_HUMANA
        acao.proximo_passo_tipo = ProximoPassoTipoEnum.REDIRECIONAR_LINK
        acao.proximo_passo_instrucao = "Clique no link para enviar a mensagem no WhatsApp"
        acao.proximo_passo_dados = {
            "link": "https://wa.me/5511999999999?text=Ol%C3%A1%2C%20esta%20%C3%A9%20uma%20mensagem%20de%20press%C3%A3o",
            "texto": "Olá, esta é uma mensagem de pressão sobre o tema X"
        }
        logger.info("Link WhatsApp gerado", acao_id=str(acao.id))
    
    async def _estrategia_instagram(self, acao: Acao):
        """Estratégia para Instagram (Manual)."""
        # Mock: gera texto para manual
        acao.status = StatusAcaoEnum.AGUARDANDO_ACAO_HUMANA
        acao.proximo_passo_tipo = ProximoPassoTipoEnum.EXIBIR_TEXTO_E_ABRIR_PERFIL
        acao.proximo_passo_instrucao = "Copie o texto e envie no perfil do Instagram"
        acao.proximo_passo_dados = {
            "perfil": "@alvo_instagram",
            "texto": "Olá, esta é uma mensagem de pressão sobre o tema X. Por favor, considere nossa demanda.",
            "url_perfil": "https://instagram.com/alvo_instagram"
        }
        logger.info("Texto Instagram gerado", acao_id=str(acao.id))

orquestrador = OrquestradorCanais()