from unittest.mock import patch
from uuid import UUID

import pytest
from sqlalchemy import select

from pressao_api.core.security import get_current_user
from pressao_api.main import app
from pressao_api.models.campanha import Campanha
from pressao_api.schemas.acao import CanalEnum


class TestContadorAcoesConfirmadas:
    @pytest.fixture
    def setup_data(self, client, db_session, mock_admin):
        app.dependency_overrides[get_current_user] = lambda: mock_admin

        campanha = client.post("/api/v1/campanhas/", json={"nome": "Campanha Contador"}).json()
        alvo_whatsapp = client.post(
            "/api/v1/alvos/",
            json={
                "nome": "Alvo WhatsApp",
                "contato": "11999999999",
                "tipo_contato": "whatsapp",
                "campanha_id": campanha["id"],
            },
        ).json()
        alvo_email = client.post(
            "/api/v1/alvos/",
            json={
                "nome": "Alvo Email",
                "contato": "alvo@email.com",
                "tipo_contato": "email",
                "campanha_id": campanha["id"],
            },
        ).json()
        return {
            "campanha": campanha,
            "alvo_whatsapp": alvo_whatsapp,
            "alvo_email": alvo_email,
        }

    def test_campanha_nova_tem_contador_zero(self, client, mock_admin):
        app.dependency_overrides[get_current_user] = lambda: mock_admin

        criar = client.post("/api/v1/campanhas/", json={"nome": "Campanha Zero"})
        assert criar.status_code == 201
        campanha_id = criar.json()["id"]

        response = client.get(f"/api/v1/campanhas/{campanha_id}")
        assert response.status_code == 200
        assert response.json()["acoes_confirmadas"] == 0

    def test_confirmar_acao_incrementa_contador(self, client, mock_user, setup_data):
        app.dependency_overrides[get_current_user] = lambda: mock_user

        campanha = setup_data["campanha"]
        alvo = setup_data["alvo_whatsapp"]

        criar = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
                "canal": CanalEnum.WHATSAPP.value,
                "anonimo": False,
                "ativista": {"nome": "Teste", "email": "teste@email.com"},
            },
        )
        assert criar.status_code == 201
        acao_id = criar.json()["acao_id"]

        confirmar = client.patch(f"/api/v1/acoes/{acao_id}/confirmar")
        assert confirmar.status_code == 200
        assert confirmar.json()["acoes_confirmadas"] == 1

        campanha_resp = client.get(f"/api/v1/campanhas/{campanha['id']}")
        assert campanha_resp.status_code == 200
        assert campanha_resp.json()["acoes_confirmadas"] == 1

    def test_confirmar_duas_vezes_nao_incrementa_duplo(self, client, mock_user, setup_data):
        app.dependency_overrides[get_current_user] = lambda: mock_user

        campanha = setup_data["campanha"]
        alvo = setup_data["alvo_whatsapp"]

        criar = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
                "canal": CanalEnum.WHATSAPP.value,
                "anonimo": False,
                "ativista": {"nome": "Teste", "email": "teste@email.com"},
            },
        )
        acao_id = criar.json()["acao_id"]

        primeiro = client.patch(f"/api/v1/acoes/{acao_id}/confirmar")
        assert primeiro.status_code == 200
        assert primeiro.json()["acoes_confirmadas"] == 1

        segundo = client.patch(f"/api/v1/acoes/{acao_id}/confirmar")
        assert segundo.status_code == 400

        campanha_resp = client.get(f"/api/v1/campanhas/{campanha['id']}")
        assert campanha_resp.json()["acoes_confirmadas"] == 1

    def test_webhook_delivered_incrementa_contador(self, client, mock_admin, setup_data):
        app.dependency_overrides[get_current_user] = lambda: mock_admin

        campanha = setup_data["campanha"]
        alvo = setup_data["alvo_email"]

        criar = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
                "canal": CanalEnum.EMAIL.value,
                "anonimo": False,
                "ativista": {"nome": "Maria Silva", "email": "maria@email.com"},
            },
        )
        assert criar.status_code == 201
        acao_id = criar.json()["acao_id"]

        with patch(
            "pressao_api.api.v1.endpoints.webhooks.verificar_assinatura_sendgrid",
            return_value=True,
        ):
            response = client.post(
                "/api/v1/webhooks/sendgrid",
                json=[{"event": "delivered", "acao_id": acao_id, "sg_message_id": "sg-1"}],
            )
        assert response.status_code == 200
        assert response.json()["entregues"] == 1

        campanha_resp = client.get(f"/api/v1/campanhas/{campanha['id']}")
        assert campanha_resp.json()["acoes_confirmadas"] == 1

    def test_webhook_duplicado_nao_incrementa_duplo(self, client, mock_admin, setup_data):
        app.dependency_overrides[get_current_user] = lambda: mock_admin

        campanha = setup_data["campanha"]
        alvo = setup_data["alvo_email"]

        criar = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
                "canal": CanalEnum.EMAIL.value,
                "anonimo": False,
                "ativista": {"nome": "Maria Silva", "email": "maria@email.com"},
            },
        )
        acao_id = criar.json()["acao_id"]

        with patch(
            "pressao_api.api.v1.endpoints.webhooks.verificar_assinatura_sendgrid",
            return_value=True,
        ):
            primeiro = client.post(
                "/api/v1/webhooks/sendgrid",
                json=[{"event": "delivered", "acao_id": acao_id}],
            )
            segundo = client.post(
                "/api/v1/webhooks/sendgrid",
                json=[{"event": "delivered", "acao_id": acao_id}],
            )

        assert primeiro.status_code == 200
        assert primeiro.json()["entregues"] == 1
        assert segundo.status_code == 200
        assert segundo.json()["ignorados"] == 1

        campanha_resp = client.get(f"/api/v1/campanhas/{campanha['id']}")
        assert campanha_resp.json()["acoes_confirmadas"] == 1

    @pytest.mark.asyncio
    async def test_reconciliar_contador_corrige_divergencia(
        self, client, db_session, mock_admin, setup_data
    ):
        app.dependency_overrides[get_current_user] = lambda: mock_admin

        campanha = setup_data["campanha"]
        alvo = setup_data["alvo_whatsapp"]

        criar = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
                "canal": CanalEnum.WHATSAPP.value,
                "anonimo": False,
                "ativista": {"nome": "Teste", "email": "teste@email.com"},
            },
        )
        acao_id = criar.json()["acao_id"]
        confirmar = client.patch(f"/api/v1/acoes/{acao_id}/confirmar")
        assert confirmar.status_code == 200
        assert confirmar.json()["acoes_confirmadas"] == 1

        result = await db_session.execute(
            select(Campanha).where(Campanha.id == UUID(campanha["id"]))
        )
        entidade = result.scalar_one()
        entidade.acoes_confirmadas = 0
        await db_session.flush()

        campanha_antes = client.get(f"/api/v1/campanhas/{campanha['id']}")
        assert campanha_antes.json()["acoes_confirmadas"] == 0

        reconciliar = client.post(f"/api/v1/campanhas/{campanha['id']}/reconciliar-contador")
        assert reconciliar.status_code == 200
        body = reconciliar.json()
        assert body["antes"] == 0
        assert body["depois"] == 1
        assert body["divergencia"] == 1

        campanha_depois = client.get(f"/api/v1/campanhas/{campanha['id']}")
        assert campanha_depois.json()["acoes_confirmadas"] == 1

    def test_reconciliar_requer_admin(self, client, mock_user, setup_data):
        app.dependency_overrides[get_current_user] = lambda: mock_user

        campanha = setup_data["campanha"]
        response = client.post(f"/api/v1/campanhas/{campanha['id']}/reconciliar-contador")
        assert response.status_code == 403
