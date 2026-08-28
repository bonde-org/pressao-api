import pytest

from pressao_api.core.security import get_current_user
from pressao_api.main import app
from pressao_api.schemas.acao import CanalEnum


class TestAPI:
    """Testes de integração da API."""

    @pytest.fixture
    def setup_data(self, client, db_session, mock_admin):
        """Cria campanha e alvo para os testes de ação"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin

        # Cria campanha
        campanha_resp = client.post("/api/v1/campanhas/", json={"nome": "Campanha Teste Ação"})
        campanha = campanha_resp.json()

        # Cria alvo do tipo email
        alvo_resp = client.post(
            "/api/v1/alvos/",
            json={
                "nome": "Alvo Teste",
                "contato": "teste@email.com",
                "tipo_contato": "email",
                "campanha_id": campanha["id"],
            },
        )
        alvo = alvo_resp.json()

        # Cria alvo do tipo whatsapp
        alvo_whatsapp_resp = client.post(
            "/api/v1/alvos/",
            json={
                "nome": "Alvo WhatsApp",
                "contato": "11999999999",
                "tipo_contato": "whatsapp",
                "campanha_id": campanha["id"],
            },
        )
        alvo_whatsapp = alvo_whatsapp_resp.json()

        return {"campanha": campanha, "alvo_email": alvo, "alvo_whatsapp": alvo_whatsapp}

    def test_criar_acao_email(self, client, db_session, mock_user, setup_data):
        """Testa criação de ação por email."""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        campanha = setup_data["campanha"]
        alvo = setup_data["alvo_email"]

        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
                "canal": CanalEnum.EMAIL.value,
                "anonimo": False,
                "ativista": {"nome": "Teste", "email": "teste@email.com"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status_atual"] == "PROCESSANDO"
        assert data["proximo_passo"]["tipo"] == "WEBHOOK_AGUARDAR"

    def test_criar_acao_whatsapp(self, client, db_session, mock_user, setup_data):
        """Testa criação de ação por WhatsApp."""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        campanha = setup_data["campanha"]
        alvo = setup_data["alvo_whatsapp"]

        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
                "canal": CanalEnum.WHATSAPP.value,
                "anonimo": False,
                "ativista": {"nome": "Teste", "email": "teste@email.com"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status_atual"] == "AGUARDANDO_ACAO_HUMANA"
        assert data["proximo_passo"]["tipo"] == "REDIRECIONAR_LINK"
        assert "link" in data["proximo_passo"]["dados"]

    def test_buscar_acao(self, client, db_session, mock_user, setup_data):
        """Testa busca de ação."""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        campanha = setup_data["campanha"]
        alvo = setup_data["alvo_email"]

        # Cria ação primeiro
        create_resp = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
                "canal": CanalEnum.EMAIL.value,
                "anonimo": False,
                "ativista": {"nome": "Teste", "email": "teste@email.com"},
            },
        )
        acao_id = create_resp.json()["acao_id"]

        # Busca ação
        response = client.get(f"/api/v1/acoes/{acao_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == acao_id
        assert data["status"] == "PROCESSANDO"

    def test_buscar_status(self, client, db_session, mock_user, setup_data):
        """Testa busca de status da ação."""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        campanha = setup_data["campanha"]
        alvo = setup_data["alvo_email"]

        # Cria ação
        create_resp = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
                "canal": CanalEnum.EMAIL.value,
                "anonimo": False,
                "ativista": {"nome": "Teste", "email": "teste@email.com"},
            },
        )
        acao_id = create_resp.json()["acao_id"]

        # Busca status
        response = client.get(f"/api/v1/acoes/{acao_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == acao_id
        assert "status" in data

    def test_confirmar_acao(self, client, db_session, mock_user, setup_data):
        """Testa confirmação de ação manual."""
        app.dependency_overrides[get_current_user] = lambda: mock_user

        campanha = setup_data["campanha"]
        alvo = setup_data["alvo_whatsapp"]

        # Cria ação WhatsApp (manual)
        create_resp = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
                "canal": CanalEnum.WHATSAPP.value,
                "anonimo": False,
                "ativista": {"nome": "Teste", "email": "teste@email.com"},
            },
        )
        acao_id = create_resp.json()["acao_id"]

        # Confirma ação
        response = client.patch(f"/api/v1/acoes/{acao_id}/confirmar")
        assert response.status_code == 204

        # Verifica status atualizado
        status_resp = client.get(f"/api/v1/acoes/{acao_id}/status")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["status"] == "CONCLUIDA"
        assert data["metrica_qualidade"] is not None
