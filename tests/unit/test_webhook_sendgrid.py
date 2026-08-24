from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from pressao_api.models.acao import Acao
from pressao_api.schemas.acao import ProximoPassoTipoEnum, StatusAcaoEnum
from pressao_api.services.sendgrid_webhook import (
    processar_eventos_sendgrid,
    verificar_assinatura_sendgrid,
)


class TestAssinaturaWebhook:
    def test_sem_chave_em_development_aceita(self):
        with patch("pressao_api.services.sendgrid_webhook.settings") as mock_settings:
            mock_settings.SENDGRID_WEBHOOK_VERIFICATION_KEY = ""
            mock_settings.APP_ENV = "development"
            assert verificar_assinatura_sendgrid(b"[]", "", "") is True

    def test_sem_chave_em_production_rejeita(self):
        with patch("pressao_api.services.sendgrid_webhook.settings") as mock_settings:
            mock_settings.SENDGRID_WEBHOOK_VERIFICATION_KEY = ""
            mock_settings.APP_ENV = "production"
            assert verificar_assinatura_sendgrid(b"[]", "sig", "ts") is False

    def test_com_chave_sem_headers_rejeita(self):
        with patch("pressao_api.services.sendgrid_webhook.settings") as mock_settings:
            mock_settings.SENDGRID_WEBHOOK_VERIFICATION_KEY = "MFkwEwYHKoZIzj0CAQY..."
            mock_settings.APP_ENV = "production"
            assert verificar_assinatura_sendgrid(b"[]", "", "") is False

    def test_assinatura_valida_delega_ao_sdk(self):
        with (
            patch("pressao_api.services.sendgrid_webhook.settings") as mock_settings,
            patch("pressao_api.services.sendgrid_webhook.EventWebhook") as mock_cls,
        ):
            mock_settings.SENDGRID_WEBHOOK_VERIFICATION_KEY = "chave-publica"
            mock_settings.APP_ENV = "production"
            instance = mock_cls.return_value
            instance.convert_public_key_to_ecdsa.return_value = "ec-key"
            instance.verify_signature.return_value = True

            assert verificar_assinatura_sendgrid(b'[{"event":"delivered"}]', "sig", "123") is True
            instance.verify_signature.assert_called_once()

    def test_sdk_levanta_excecao_retorna_false(self):
        with (
            patch("pressao_api.services.sendgrid_webhook.settings") as mock_settings,
            patch("pressao_api.services.sendgrid_webhook.EventWebhook") as mock_cls,
        ):
            mock_settings.SENDGRID_WEBHOOK_VERIFICATION_KEY = "chave-publica"
            mock_settings.APP_ENV = "production"
            mock_cls.return_value.convert_public_key_to_ecdsa.side_effect = ValueError("bad key")
            assert verificar_assinatura_sendgrid(b"[]", "sig", "123") is False


class TestProcessarEventos:
    @pytest.mark.asyncio
    async def test_delivered_conclui_acao(self):
        acao_id = uuid4()
        acao = Acao(
            id=acao_id,
            campanha_id=uuid4(),
            alvo_id=uuid4(),
            canal="email",
            status=StatusAcaoEnum.PROCESSANDO,
            proximo_passo_dados={},
        )
        repo = MagicMock()
        repo.buscar_por_id = MagicMock(return_value=acao)

        async def buscar(aid):
            return acao

        async def salvar(a):
            return a

        repo.buscar_por_id = buscar
        repo.salvar = salvar

        async def incrementar(campanha_id):
            return 1

        campanha_repo = MagicMock()
        campanha_repo.incrementar_acoes_confirmadas = incrementar

        resumo = await processar_eventos_sendgrid(
            [{"event": "delivered", "acao_id": str(acao_id), "sg_message_id": "sg-1"}],
            repo,
            campanha_repo,
        )

        assert resumo["entregues"] == 1
        assert acao.status == StatusAcaoEnum.CONCLUIDA
        assert acao.proximo_passo_tipo == ProximoPassoTipoEnum.FINALIZADO
        assert acao.confirmado_em is not None

    @pytest.mark.asyncio
    async def test_bounce_marca_falha(self):
        acao_id = uuid4()
        acao = Acao(
            id=acao_id,
            campanha_id=uuid4(),
            alvo_id=uuid4(),
            canal="email",
            status=StatusAcaoEnum.PROCESSANDO,
            proximo_passo_dados={},
        )

        async def buscar(aid):
            return acao

        async def salvar(a):
            return a

        repo = MagicMock()
        repo.buscar_por_id = buscar
        repo.salvar = salvar

        resumo = await processar_eventos_sendgrid(
            [{"event": "bounce", "acao_id": str(acao_id), "reason": "mailbox full"}],
            repo,
        )

        assert resumo["falhas"] == 1
        assert acao.status == StatusAcaoEnum.FALHA
        assert "mailbox full" in acao.proximo_passo_instrucao

    @pytest.mark.asyncio
    async def test_sem_acao_id_ignora(self):
        repo = MagicMock()

        async def buscar(aid):
            raise AssertionError("não deveria buscar")

        repo.buscar_por_id = buscar
        repo.salvar = MagicMock()

        resumo = await processar_eventos_sendgrid([{"event": "delivered"}], repo)
        assert resumo["ignorados"] == 1
        assert resumo["processados"] == 0

    @pytest.mark.asyncio
    async def test_open_apenas_registra(self):
        acao_id = uuid4()
        acao = Acao(
            id=acao_id,
            campanha_id=uuid4(),
            alvo_id=uuid4(),
            canal="email",
            status=StatusAcaoEnum.PROCESSANDO,
            proximo_passo_dados={},
        )

        async def buscar(aid):
            return acao

        saved = []

        async def salvar(a):
            saved.append(a)
            return a

        repo = MagicMock()
        repo.buscar_por_id = buscar
        repo.salvar = salvar

        resumo = await processar_eventos_sendgrid(
            [{"event": "open", "unique_args": {"acao_id": str(acao_id)}}],
            repo,
        )

        assert resumo["processados"] == 1
        assert acao.status == StatusAcaoEnum.PROCESSANDO
        assert acao.proximo_passo_dados["ultimo_evento"] == "open"
        assert len(saved) == 1
