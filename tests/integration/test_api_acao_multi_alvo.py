import pytest

from pressao_api.core.security import get_current_user
from pressao_api.main import app
from pressao_api.schemas.acao import CanalEnum, StatusAcaoEnum, TipoAcaoEnum


class TestAcaoMultiAlvo:
    @pytest.fixture
    def setup_campanha_email(self, client, db_session, mock_admin):
        app.dependency_overrides[get_current_user] = lambda: mock_admin

        campanha = client.post("/api/v1/campanhas/", json={"nome": "Campanha Multi Alvo"}).json()
        campanha_id = campanha["id"]

        for i, email in enumerate(["a1@email.com", "a2@email.com"]):
            client.post(
                "/api/v1/alvos/",
                json={
                    "nome": f"Alvo {i}",
                    "contato": email,
                    "tipo_contato": "email",
                    "campanha_id": campanha_id,
                },
            )

        alvos_resp = client.get(f"/api/v1/alvos/campanha/{campanha_id}")
        agregado = alvos_resp.json()[0]
        assert agregado["modo"] == "agregado"
        assert agregado["total_membros"] == 2

        return {"campanha": campanha, "agregado": agregado}

    def test_criar_acao_multi_alvo_concluida(
        self, client, db_session, mock_user, setup_campanha_email
    ):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        campanha = setup_campanha_email["campanha"]
        agregado = setup_campanha_email["agregado"]

        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": agregado["id"],
                "canal": CanalEnum.EMAIL.value,
                "anonimo": False,
                "ativista": {"nome": "Teste", "email": "ativista@email.com"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tipo_acao"] == TipoAcaoEnum.MULTI_ALVO.value
        assert data["status_atual"] == StatusAcaoEnum.CONCLUIDA.value
        assert data["proximo_passo"]["tipo"] == "FINALIZADO"
        assert data["disparos_resumo"]["total"] == 2
        assert data["disparos_resumo"]["enviados"] == 2

        campanha_resp = client.get(f"/api/v1/campanhas/{campanha['id']}")
        assert campanha_resp.json()["acoes_confirmadas"] == 1

    def test_listar_alvos_agrega_emails(self, client, db_session, mock_admin, setup_campanha_email):
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        campanha_id = setup_campanha_email["campanha"]["id"]

        response = client.get(f"/api/v1/alvos/campanha/{campanha_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["modo"] == "agregado"
        assert data[0]["total_membros"] == 2
