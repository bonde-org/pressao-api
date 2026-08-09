import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from pressao_api.main import app
from pressao_api.core.database import get_db
from pressao_api.core.security import get_current_user, get_current_user_optional

class TestAPIAnonima:
    
    def test_criar_acao_anonima_com_service_account(self, client, db_session, mock_service_account):
        """Service account pode criar ação anônima"""
        app.dependency_overrides[get_current_user] = lambda: mock_service_account
        
        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": str(uuid4()),
                "alvo_id": str(uuid4()),
                "canal": "whatsapp",
                "anonimo": True
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["anonimo"] is True
        assert data["ativista_id"] is None
        assert data["ativista_nome"] is None

    def test_criar_acao_anonima_sem_autenticacao_deve_falhar(self, client, db_session):
        """Usuário sem autenticação NÃO pode criar ação"""
        # Remove o override para usar autenticação real
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_user_optional, None)
        
        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": str(uuid4()),
                "alvo_id": str(uuid4()),
                "canal": "whatsapp",
                "anonimo": True
            }
        )
        assert response.status_code == 401  # Não autenticado

    def test_criar_acao_com_dados_ativista(self, client, db_session, mock_service_account):
        """Service account pode criar ação com dados do ativista"""
        app.dependency_overrides[get_current_user] = lambda: mock_service_account
        
        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": str(uuid4()),
                "alvo_id": str(uuid4()),
                "canal": "email",
                "ativista": {
                    "nome": "João Silva",
                    "email": "joao@email.com"
                }
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["anonimo"] is False
        assert data["ativista_nome"] == "João Silva"
        assert data["ativista_email"] == "joao@email.com"
        assert data["ativista_id"] is None  # Service account não é o ativista

    def test_criar_acao_com_ativista_logado(self, client, db_session, mock_user):
        """Usuário logado tem ativista_id preenchido automaticamente"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": str(uuid4()),
                "alvo_id": str(uuid4()),
                "canal": "instagram"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["ativista_id"] == "test-user-123"
        assert data["anonimo"] is False

    def test_ativista_logado_com_dados_extra(self, client, db_session, mock_user):
        """Ativista logado pode fornecer dados extras opcionais"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": str(uuid4()),
                "alvo_id": str(uuid4()),
                "canal": "email",
                "ativista": {
                    "nome": "Nome Diferente",
                    "email": "outro@email.com"
                },
                "anonimo": False
            }
        )
        assert response.status_code == 201
        data = response.json()
        # Dados do usuário logado prevalecem
        assert data["ativista_id"] == "test-user-123"

    def test_ativista_anonimo_com_dados_deve_ignorar(self, client, db_session, mock_user):
        """Se anonimo=True, dados do ativista são ignorados"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        data_json = {
            "campanha_id": str(uuid4()),
            "alvo_id": str(uuid4()),
            "canal": "whatsapp",
            "anonimo": True,
            "ativista": {
                "nome": "João Silva",
                "email": "joao@email.com"
            }
        }
        response = client.post(
            "/api/v1/acoes/",
            json=data_json
        )
        assert response.status_code == 201
        data = response.json()
        
        assert data["anonimo"] is True
        assert data["ativista_nome"] is None
        assert data["ativista_email"] is None