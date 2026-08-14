from unittest.mock import patch

from pressao_api.core.security import get_current_user
from pressao_api.main import app
from pressao_api.schemas.acao import CanalEnum


class TestWebhookSendGridAPI:
    def test_assinatura_invalida_retorna_401(self, client):
        with patch(
            "pressao_api.api.v1.endpoints.webhooks.verificar_assinatura_sendgrid",
            return_value=False,
        ):
            response = client.post(
                "/api/v1/webhooks/sendgrid",
                content=b"[]",
                headers={"Content-Type": "application/json"},
            )
        assert response.status_code == 401

    def test_payload_nao_lista_retorna_400(self, client):
        with patch(
            "pressao_api.api.v1.endpoints.webhooks.verificar_assinatura_sendgrid",
            return_value=True,
        ):
            response = client.post(
                "/api/v1/webhooks/sendgrid",
                json={"event": "delivered"},
            )
        assert response.status_code == 400

    def test_delivered_atualiza_acao(self, client, db_session, mock_admin):
        app.dependency_overrides[get_current_user] = lambda: mock_admin

        campanha = client.post("/api/v1/campanhas/", json={"nome": "Campanha Webhook"}).json()
        alvo = client.post(
            "/api/v1/alvos/",
            json={
                "nome": "Alvo Email",
                "contato": "alvo@email.com",
                "tipo_contato": "email",
                "campanha_id": campanha["id"],
            },
        ).json()
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
                json=[{"event": "delivered", "acao_id": acao_id, "sg_message_id": "sg-xyz"}],
            )

        assert response.status_code == 200
        body = response.json()
        assert body["entregues"] == 1

        status_resp = client.get(f"/api/v1/acoes/{acao_id}/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "CONCLUIDA"
