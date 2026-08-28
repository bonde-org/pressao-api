import uuid

import pytest

from pressao_api.core.security import get_current_user
from pressao_api.main import app
from pressao_api.schemas.acao import CanalEnum


class TestAtualizacaoRetroativa:
    """Testes para atualização retroativa de dados do ativista por sessão."""

    @pytest.fixture
    def setup_data(self, client, db_session, mock_admin):
        app.dependency_overrides[get_current_user] = lambda: mock_admin

        campanha_resp = client.post("/api/v1/campanhas/", json={"nome": "Campanha Retroativa"})
        campanha = campanha_resp.json()

        alvo_email_resp = client.post(
            "/api/v1/alvos/",
            json={
                "nome": "Alvo Email",
                "contato": "alvo@email.com",
                "tipo_contato": "email",
                "campanha_id": campanha["id"],
            },
        )

        alvo_instagram_resp = client.post(
            "/api/v1/alvos/",
            json={
                "nome": "Alvo Instagram",
                "contato": "alvo_insta",
                "tipo_contato": "instagram",
                "campanha_id": campanha["id"],
            },
        )

        return {
            "campanha": campanha,
            "alvo_email": alvo_email_resp.json(),
            "alvo_instagram": alvo_instagram_resp.json(),
        }

    def test_acao_sem_ativista_nao_e_anonima(
        self, client, db_session, mock_service_account, setup_data
    ):
        """Ação sem dados de ativista mas com sessao_id não é marcada como anônima."""
        app.dependency_overrides[get_current_user] = lambda: mock_service_account

        sessao_id = str(uuid.uuid4())
        campanha = setup_data["campanha"]
        alvo_instagram = setup_data["alvo_instagram"]

        resp = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo_instagram["id"],
                "canal": CanalEnum.INSTAGRAM.value,
                "sessao_id": sessao_id,
                "anonimo": False,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["anonimo"] is False
        assert data["ativista_nome"] is None

    def test_acoes_anteriores_atualizadas_com_dados_ativista(
        self, client, db_session, mock_service_account, setup_data
    ):
        """Ações sem ativista (não anônimas) da mesma sessão são atualizadas."""
        app.dependency_overrides[get_current_user] = lambda: mock_service_account

        sessao_id = str(uuid.uuid4())
        campanha = setup_data["campanha"]
        alvo_instagram = setup_data["alvo_instagram"]
        alvo_email = setup_data["alvo_email"]

        # Ação sem ativista (não anônima)
        resp1 = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo_instagram["id"],
                "canal": CanalEnum.INSTAGRAM.value,
                "sessao_id": sessao_id,
                "anonimo": False,
            },
        )
        assert resp1.status_code == 201
        acao1_id = resp1.json()["acao_id"]

        # Ação com ativista (primeiro preenchimento)
        resp2 = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo_email["id"],
                "canal": CanalEnum.EMAIL.value,
                "sessao_id": sessao_id,
                "anonimo": False,
                "ativista": {"nome": "Maria", "email": "maria@email.com"},
            },
        )
        assert resp2.status_code == 201

        # Verifica que ação anterior foi atualizada
        app.dependency_overrides[get_current_user] = lambda: {
            **mock_service_account,
            "is_admin": True,
        }
        acao1_resp = client.get(f"/api/v1/acoes/{acao1_id}")
        assert acao1_resp.status_code == 200
        acao1 = acao1_resp.json()
        assert acao1["ativista_nome"] == "Maria"
        assert acao1["ativista_email"] == "maria@email.com"

    def test_acoes_anonimas_nao_atualizadas_retroativamente(
        self, client, db_session, mock_service_account, setup_data
    ):
        """Ações explicitamente anônimas nunca são atualizadas retroativamente."""
        app.dependency_overrides[get_current_user] = lambda: mock_service_account

        sessao_id = str(uuid.uuid4())
        campanha = setup_data["campanha"]
        alvo_instagram = setup_data["alvo_instagram"]
        alvo_email = setup_data["alvo_email"]

        # Ação explicitamente anônima
        resp1 = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo_instagram["id"],
                "canal": CanalEnum.INSTAGRAM.value,
                "sessao_id": sessao_id,
                "anonimo": True,
            },
        )
        assert resp1.status_code == 201
        acao1_id = resp1.json()["acao_id"]

        # Ação com ativista na mesma sessão
        client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo_email["id"],
                "canal": CanalEnum.EMAIL.value,
                "sessao_id": sessao_id,
                "anonimo": False,
                "ativista": {"nome": "Maria", "email": "maria@email.com"},
            },
        )

        # Ação anônima NÃO deve ter sido atualizada
        app.dependency_overrides[get_current_user] = lambda: {
            **mock_service_account,
            "is_admin": True,
        }
        acao1_resp = client.get(f"/api/v1/acoes/{acao1_id}")
        assert acao1_resp.status_code == 200
        acao1 = acao1_resp.json()
        assert acao1["ativista_nome"] is None
        assert acao1["ativista_email"] is None
        assert acao1["anonimo"] is True

    def test_acoes_outra_sessao_nao_afetadas(
        self, client, db_session, mock_service_account, setup_data
    ):
        """Ações de outra sessão não são atualizadas."""
        app.dependency_overrides[get_current_user] = lambda: mock_service_account

        sessao_a = str(uuid.uuid4())
        sessao_b = str(uuid.uuid4())
        campanha = setup_data["campanha"]
        alvo_instagram = setup_data["alvo_instagram"]
        alvo_email = setup_data["alvo_email"]

        resp_a = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo_instagram["id"],
                "canal": CanalEnum.INSTAGRAM.value,
                "sessao_id": sessao_a,
                "anonimo": False,
            },
        )
        assert resp_a.status_code == 201
        acao_a_id = resp_a.json()["acao_id"]

        client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo_email["id"],
                "canal": CanalEnum.EMAIL.value,
                "sessao_id": sessao_b,
                "anonimo": False,
                "ativista": {"nome": "João", "email": "joao@email.com"},
            },
        )

        app.dependency_overrides[get_current_user] = lambda: {
            **mock_service_account,
            "is_admin": True,
        }
        acao_a_resp = client.get(f"/api/v1/acoes/{acao_a_id}")
        assert acao_a_resp.status_code == 200
        acao_a = acao_a_resp.json()
        assert acao_a["ativista_nome"] is None

    def test_acoes_com_ativista_nao_sobrescritas(
        self, client, db_session, mock_service_account, setup_data
    ):
        """Ações que já têm dados de ativista não são sobrescritas."""
        app.dependency_overrides[get_current_user] = lambda: mock_service_account

        sessao_id = str(uuid.uuid4())
        campanha = setup_data["campanha"]
        alvo_email = setup_data["alvo_email"]

        resp1 = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo_email["id"],
                "canal": CanalEnum.EMAIL.value,
                "sessao_id": sessao_id,
                "anonimo": False,
                "ativista": {"nome": "Ana", "email": "ana@email.com"},
            },
        )
        assert resp1.status_code == 201
        acao1_id = resp1.json()["acao_id"]

        resp2 = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo_email["id"],
                "canal": CanalEnum.EMAIL.value,
                "sessao_id": sessao_id,
                "anonimo": False,
                "ativista": {"nome": "Carlos", "email": "carlos@email.com"},
            },
        )
        assert resp2.status_code == 201

        app.dependency_overrides[get_current_user] = lambda: {
            **mock_service_account,
            "is_admin": True,
        }
        acao1_resp = client.get(f"/api/v1/acoes/{acao1_id}")
        assert acao1_resp.status_code == 200
        acao1 = acao1_resp.json()
        assert acao1["ativista_nome"] == "Ana"

    def test_sessao_id_invalido_rejeitado(self, client, db_session, mock_service_account, setup_data):
        """sessao_id com formato inválido é rejeitado."""
        app.dependency_overrides[get_current_user] = lambda: mock_service_account

        campanha = setup_data["campanha"]
        alvo_email = setup_data["alvo_email"]

        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo_email["id"],
                "canal": CanalEnum.EMAIL.value,
                "sessao_id": "nao-e-uuid",
                "anonimo": False,
                "ativista": {"nome": "Teste", "email": "teste@email.com"},
            },
        )
        assert response.status_code == 422
