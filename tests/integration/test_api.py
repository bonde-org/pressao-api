import pytest
from uuid import uuid4
from pressao_api.schemas.acao import CanalEnum

class TestAPI:
    """Testes de integração da API."""
    
    def test_criar_acao_email(self, client):
        """Testa criação de ação por email."""
        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": str(uuid4()),
                "alvo_id": str(uuid4()),
                "canal": CanalEnum.EMAIL.value
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["status_atual"] == "PROCESSANDO"
        assert data["proximo_passo"]["tipo"] == "WEBHOOK_AGUARDAR"
    
    def test_criar_acao_whatsapp(self, client):
        """Testa criação de ação por WhatsApp."""
        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": str(uuid4()),
                "alvo_id": str(uuid4()),
                "canal": CanalEnum.WHATSAPP.value
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["status_atual"] == "AGUARDANDO_ACAO_HUMANA"
        assert data["proximo_passo"]["tipo"] == "REDIRECIONAR_LINK"
        assert "link" in data["proximo_passo"]["dados"]
    
    def test_buscar_acao(self, client):
        """Testa busca de ação."""
        # Cria ação primeiro
        create_resp = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": str(uuid4()),
                "alvo_id": str(uuid4()),
                "canal": CanalEnum.EMAIL.value
            }
        )
        acao_id = create_resp.json()["acao_id"]
        
        # Busca ação
        response = client.get(f"/api/v1/acoes/{acao_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == acao_id
        assert data["status"] == "PROCESSANDO"
    
    def test_buscar_status(self, client):
        """Testa busca de status da ação."""
        # Cria ação
        create_resp = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": str(uuid4()),
                "alvo_id": str(uuid4()),
                "canal": CanalEnum.EMAIL.value
            }
        )
        acao_id = create_resp.json()["acao_id"]
        
        # Busca status
        response = client.get(f"/api/v1/acoes/{acao_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == acao_id
        assert "status" in data
    
    def test_confirmar_acao(self, client):
        """Testa confirmação de ação manual."""
        # Cria ação WhatsApp (manual)
        create_resp = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": str(uuid4()),
                "alvo_id": str(uuid4()),
                "canal": CanalEnum.WHATSAPP.value
            }
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