from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sendgrid.helpers.mail import Mail

from pressao_api.models.acao import Acao
from pressao_api.models.alvo import Alvo
from pressao_api.models.campanha import Campanha
from pressao_api.services.email_service import CHAVES_PLACEHOLDER, EmailService


def _acao_alvo_campanha():
    campanha_id = uuid4()
    acao = Acao(
        id=uuid4(),
        campanha_id=campanha_id,
        alvo_id=uuid4(),
        canal="email",
        ativista_nome="Maria Silva",
        ativista_email="maria@email.com",
        anonimo=False,
    )
    alvo = Alvo(
        id=acao.alvo_id,
        nome="Deputado Exemplo",
        contato="alvo@orgao.gov.br",
        tipo_contato="email",
        campanha_id=campanha_id,
    )
    campanha = Campanha(
        id=campanha_id,
        nome="Campanha Teste",
        descricao="Descrição da campanha",
    )
    return acao, alvo, campanha


class TestValidacaoEnvio:
    def test_destinatario_invalido(self):
        service = EmailService(client=MagicMock())
        with pytest.raises(ValueError, match="Destinatário inválido"):
            service.enviar_pressao(
                destinatario="nao-e-email",
                remetente_email="ativista@email.com",
                assunto="Assunto",
                conteudo_html="<p>Olá</p>",
                acao_id=str(uuid4()),
            )

    def test_assunto_vazio(self):
        service = EmailService(client=MagicMock())
        with pytest.raises(ValueError, match="Assunto"):
            service.enviar_pressao(
                destinatario="alvo@email.com",
                remetente_email="ativista@email.com",
                assunto="   ",
                conteudo_html="<p>Olá</p>",
                acao_id=str(uuid4()),
            )

    def test_conteudo_vazio(self):
        service = EmailService(client=MagicMock())
        with pytest.raises(ValueError, match="Conteúdo HTML"):
            service.enviar_pressao(
                destinatario="alvo@email.com",
                remetente_email="ativista@email.com",
                assunto="Pressão",
                conteudo_html="",
                acao_id=str(uuid4()),
            )

    def test_remetente_invalido(self):
        service = EmailService(client=MagicMock())
        with pytest.raises(ValueError, match="Remetente"):
            service.enviar_pressao(
                destinatario="alvo@email.com",
                remetente_email="nao-e-email",
                assunto="Pressão",
                conteudo_html="<p>Olá</p>",
                acao_id=str(uuid4()),
            )

    def test_placeholder_ausente_no_template(self):
        service = EmailService(client=MagicMock())
        with pytest.raises(ValueError, match="Placeholder ausente"):
            service.enviar_pressao(
                destinatario="alvo@email.com",
                remetente_email="ativista@email.com",
                assunto="Pressão",
                conteudo_html="<p>{nome}</p>",
                acao_id=str(uuid4()),
                dados_dinamicos={},
            )


class TestSandbox:
    def test_sandbox_com_chave_placeholder_nao_chama_api(self):
        client = MagicMock()
        service = EmailService(client=client)

        with patch("pressao_api.services.email_service.settings") as mock_settings:
            mock_settings.SENDGRID_SANDBOX_MODE = True
            mock_settings.SENDGRID_API_KEY = "test-key"

            resultado = service.enviar_pressao(
                destinatario="alvo@email.com",
                remetente_email="maria@email.com",
                remetente_nome="Maria Silva",
                assunto="Pressão: Campanha",
                conteudo_html="<p>Mensagem</p>",
                acao_id=str(uuid4()),
            )

        client.send.assert_not_called()
        assert resultado.sucesso is True
        assert resultado.sandbox is True
        assert resultado.status == "sandbox"
        assert resultado.message_id.startswith("sandbox-")

    def test_sandbox_com_chave_real_habilita_sandbox_mode_e_chama_api(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.headers = {"X-Message-Id": "sg-msg-123"}
        client.send.return_value = response
        service = EmailService(client=client)

        with patch("pressao_api.services.email_service.settings") as mock_settings:
            mock_settings.SENDGRID_SANDBOX_MODE = True
            mock_settings.SENDGRID_API_KEY = "SG.chave-real"
            resultado = service.enviar_pressao(
                destinatario="alvo@email.com",
                remetente_email="maria@email.com",
                remetente_nome="Maria Silva",
                assunto="Pressão: Campanha",
                conteudo_html="<p>Mensagem</p>",
                acao_id=str(uuid4()),
            )

        client.send.assert_called_once()
        mail = client.send.call_args[0][0]
        assert isinstance(mail, Mail)
        assert mail.mail_settings.sandbox_mode.enable is True
        assert mail.from_email.email == "maria@email.com"
        assert mail.from_email.name == "Maria Silva"
        assert resultado.sucesso is True
        assert resultado.sandbox is True
        assert resultado.message_id == "sg-msg-123"

    def test_chave_placeholder_conhecida(self):
        assert "test-key" in CHAVES_PLACEHOLDER
        assert "mock-key" in CHAVES_PLACEHOLDER


class TestEnvioReal:
    def test_envio_sucesso_retorna_message_id(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 202
        response.headers = {"X-Message-Id": "abc-123"}
        client.send.return_value = response
        service = EmailService(client=client)

        with patch("pressao_api.services.email_service.settings") as mock_settings:
            mock_settings.SENDGRID_SANDBOX_MODE = False
            mock_settings.SENDGRID_API_KEY = "SG.chave-real"
            resultado = service.enviar_pressao(
                destinatario="alvo@email.com",
                remetente_email="maria@email.com",
                remetente_nome="Maria Silva",
                assunto="Pressão",
                conteudo_html="<p>Olá {alvo}</p>",
                acao_id=str(uuid4()),
                dados_dinamicos={"alvo": "João"},
                nome_destinatario="João Alvo",
            )

        client.send.assert_called_once()
        assert resultado.sucesso is True
        assert resultado.status == "enviado"
        assert resultado.message_id == "abc-123"
        assert resultado.sandbox is False

    def test_envio_http_erro_retorna_falha(self):
        client = MagicMock()
        response = MagicMock()
        response.status_code = 401
        response.body = b"unauthorized"
        response.headers = {}
        client.send.return_value = response
        service = EmailService(client=client)

        with patch("pressao_api.services.email_service.settings") as mock_settings:
            mock_settings.SENDGRID_SANDBOX_MODE = False
            mock_settings.SENDGRID_API_KEY = "SG.chave-real"
            resultado = service.enviar_pressao(
                destinatario="alvo@email.com",
                remetente_email="maria@email.com",
                assunto="Pressão",
                conteudo_html="<p>Olá</p>",
                acao_id=str(uuid4()),
            )

        assert resultado.sucesso is False
        assert resultado.status == "falha"
        assert resultado.erro is not None

    def test_montar_template_inclui_dados_dinamicos(self):
        service = EmailService(client=MagicMock())
        acao, alvo, campanha = _acao_alvo_campanha()
        html = service.montar_template_pressao(acao, alvo, campanha)
        assert "Deputado Exemplo" in html
        assert "Campanha Teste" in html
        assert "Maria Silva" in html
        assert str(acao.id) in html
