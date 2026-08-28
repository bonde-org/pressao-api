from unittest.mock import patch
from uuid import uuid4

import pytest

from pressao_api.core.security import get_current_user
from pressao_api.main import app
from pressao_api.schemas.acao import CanalEnum
from pressao_api.schemas.email import ResultadoEnvioEmail
from pressao_api.services.email_service import email_service

CONTEUDO_TEMPLATE = "<p>Prezado(a) {alvo_nome}, sobre a campanha {campanha_nome}.</p>"


@pytest.fixture
def envio_mockado():
    """Evita chamada real ao SendGrid e expõe os argumentos do envio."""
    resultado = ResultadoEnvioEmail(
        sucesso=True,
        message_id="mock-message-id",
        sandbox=True,
        status="sandbox",
        destinatario="alvo@email.com",
        remetente="ativista@email.com",
    )
    with patch.object(email_service, "enviar_pressao", return_value=resultado) as mock_enviar:
        yield mock_enviar


class TestAcaoComTemplate:
    @pytest.fixture
    def setup_data(self, client, db_session, mock_admin):
        app.dependency_overrides[get_current_user] = lambda: mock_admin

        campanha = client.post("/api/v1/campanhas/", json={"nome": "Campanha Template Ação"}).json()
        outra_campanha = client.post(
            "/api/v1/campanhas/", json={"nome": "Outra Campanha Template"}
        ).json()

        alvo_email = client.post(
            "/api/v1/alvos/",
            json={
                "nome": "Deputado Exemplo",
                "contato": "alvo@email.com",
                "tipo_contato": "email",
                "campanha_id": campanha["id"],
            },
        ).json()
        alvo_whatsapp = client.post(
            "/api/v1/alvos/",
            json={
                "nome": "Alvo WhatsApp",
                "contato": "11999999999",
                "tipo_contato": "whatsapp",
                "campanha_id": campanha["id"],
            },
        ).json()

        template = client.post(
            "/api/v1/templates/",
            json={
                "campanha_id": campanha["id"],
                "canal": "email",
                "titulo": "Assunto vindo do template",
                "conteudo": CONTEUDO_TEMPLATE,
                "ativo": True,
            },
        ).json()
        template_inativo = client.post(
            "/api/v1/templates/",
            json={
                "campanha_id": campanha["id"],
                "canal": "email",
                "titulo": "Template inativo",
                "conteudo": CONTEUDO_TEMPLATE,
                "ativo": False,
            },
        ).json()
        template_outra_campanha = client.post(
            "/api/v1/templates/",
            json={
                "campanha_id": outra_campanha["id"],
                "canal": "email",
                "titulo": "Template de outra campanha",
                "conteudo": CONTEUDO_TEMPLATE,
                "ativo": True,
            },
        ).json()
        template_whatsapp = client.post(
            "/api/v1/templates/",
            json={
                "campanha_id": campanha["id"],
                "canal": "whatsapp",
                "titulo": "Template de WhatsApp",
                "conteudo": "Mensagem de WhatsApp",
                "ativo": True,
            },
        ).json()

        return {
            "campanha": campanha,
            "alvo_email": alvo_email,
            "alvo_whatsapp": alvo_whatsapp,
            "template": template,
            "template_inativo": template_inativo,
            "template_outra_campanha": template_outra_campanha,
            "template_whatsapp": template_whatsapp,
        }

    def _payload(self, setup_data, template_id=None, canal=CanalEnum.EMAIL.value, alvo=None):
        payload = {
            "campanha_id": setup_data["campanha"]["id"],
            "alvo_id": (alvo or setup_data["alvo_email"])["id"],
            "canal": canal,
            "anonimo": False,
            "ativista": {"nome": "Maria Silva", "email": "maria@email.com"},
        }
        if template_id is not None:
            payload["template_id"] = template_id
        return payload

    def test_criar_acao_com_template_valido(
        self, client, db_session, mock_user, setup_data, envio_mockado
    ):
        """Ação com template válido é criada e persiste o template_id"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        template = setup_data["template"]

        response = client.post("/api/v1/acoes/", json=self._payload(setup_data, template["id"]))

        assert response.status_code == 201
        acao_id = response.json()["acao_id"]

        detalhe = client.get(f"/api/v1/acoes/{acao_id}")
        assert detalhe.status_code == 200
        assert detalhe.json()["template_id"] == template["id"]

    def test_email_usa_titulo_como_assunto_e_conteudo_como_corpo(
        self, client, db_session, mock_user, setup_data, envio_mockado
    ):
        """Assunto vem do titulo e o corpo vem do conteudo do template"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        template = setup_data["template"]

        response = client.post("/api/v1/acoes/", json=self._payload(setup_data, template["id"]))

        assert response.status_code == 201
        envio_mockado.assert_called_once()
        kwargs = envio_mockado.call_args.kwargs
        assert kwargs["assunto"] == "Assunto vindo do template"
        assert "Deputado Exemplo" in kwargs["conteudo_html"]
        assert "Campanha Template Ação" in kwargs["conteudo_html"]
        assert "{alvo_nome}" not in kwargs["conteudo_html"]

    def test_acao_sem_template_usa_assunto_padrao(
        self, client, db_session, mock_user, setup_data, envio_mockado
    ):
        """Sem template_id o comportamento anterior é preservado"""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.post("/api/v1/acoes/", json=self._payload(setup_data))

        assert response.status_code == 201
        kwargs = envio_mockado.call_args.kwargs
        assert kwargs["assunto"] == "Pressão: Campanha Template Ação"

    def test_proximo_passo_expoe_template_id(
        self, client, db_session, mock_user, setup_data, envio_mockado
    ):
        """template_id fica rastreável no proximo_passo_dados"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        template = setup_data["template"]

        response = client.post("/api/v1/acoes/", json=self._payload(setup_data, template["id"]))

        assert response.status_code == 201
        assert response.json()["proximo_passo"]["dados"]["template_id"] == template["id"]

    def test_template_inexistente_retorna_404(
        self, client, db_session, mock_user, setup_data, envio_mockado
    ):
        """template_id inexistente devolve 404"""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.post("/api/v1/acoes/", json=self._payload(setup_data, str(uuid4())))

        assert response.status_code == 404
        assert "Template não encontrado" in response.text

    def test_template_de_outra_campanha_retorna_400(
        self, client, db_session, mock_user, setup_data, envio_mockado
    ):
        """Template de outra campanha é rejeitado"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        template = setup_data["template_outra_campanha"]

        response = client.post("/api/v1/acoes/", json=self._payload(setup_data, template["id"]))

        assert response.status_code == 400
        assert "não pertence à campanha" in response.text

    def test_template_inativo_retorna_400(
        self, client, db_session, mock_user, setup_data, envio_mockado
    ):
        """Template inativo é rejeitado"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        template = setup_data["template_inativo"]

        response = client.post("/api/v1/acoes/", json=self._payload(setup_data, template["id"]))

        assert response.status_code == 400
        assert "Template inativo" in response.text

    def test_template_de_canal_incompativel_retorna_400(
        self, client, db_session, mock_user, setup_data, envio_mockado
    ):
        """Template de WhatsApp não pode ser usado em ação de e-mail"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        template = setup_data["template_whatsapp"]

        response = client.post("/api/v1/acoes/", json=self._payload(setup_data, template["id"]))

        assert response.status_code == 400
        assert "canal" in response.text.lower()

    def test_template_nao_e_enviado_quando_acao_falha_de_validacao(
        self, client, db_session, mock_user, setup_data, envio_mockado
    ):
        """Validação de template acontece antes do disparo"""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        client.post("/api/v1/acoes/", json=self._payload(setup_data, str(uuid4())))

        envio_mockado.assert_not_called()
