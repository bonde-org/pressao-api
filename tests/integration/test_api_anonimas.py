import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from pressao_api.main import app
from pressao_api.core.database import get_db
from pressao_api.core.security import get_current_user, get_current_user_optional

class TestAPIAnonima:
    
    @pytest.fixture
    def setup_data(self, client, db_session, mock_admin):
        """Cria campanha e alvos para testes"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        # Cria campanha
        campanha_resp = client.post(
            "/api/v1/campanhas/",
            json={"nome": "Campanha Teste Validações"}
        )
        campanha = campanha_resp.json()
        
        # Cria alvos de diferentes tipos
        alvos = {}
        for tipo in ["email", "telefone", "whatsapp", "instagram"]:
            if tipo == "instagram":
                contato = "@instagram"
            elif tipo == "whatsapp":
                contato = "11998877666"
            elif tipo == "telefone":
                contato = "11998877887"
            elif tipo == "email":
                contato = "test@email.com"

            resp = client.post(
                "/api/v1/alvos/",
                json={
                    "nome": f"Alvo {tipo}",
                    "contato": contato,
                    "tipo_contato": tipo,
                    "campanha_id": campanha["id"]
                }
            )
            # Verifica se a resposta é válida
            if resp.status_code != 201:
                raise Exception(f"Falha ao criar alvo {tipo}: {resp.text}")
            alvos[tipo] = resp.json()
            # Verifica se tem ID
            assert "id" in alvos[tipo], f"Alvo {tipo} sem ID: {alvos[tipo]}"
        
        return {"campanha": campanha, "alvos": alvos}
    
    def test_criar_acao_anonima_com_service_account(self, client, db_session, mock_service_account, setup_data):
        """Service account pode criar ação anônima"""
        app.dependency_overrides[get_current_user] = lambda: mock_service_account
        
        campanha = setup_data["campanha"]
        alvo = setup_data["alvos"]["whatsapp"]
        
        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
                "canal": "whatsapp",
                "anonimo": True
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["anonimo"] is True
        assert data["ativista_id"] is None
        assert data["ativista_nome"] is None

    def test_criar_acao_sem_autenticacao_deve_falhar(self, client, db_session, setup_data):
        """Qualquer requisição sem token deve falhar (401)"""
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_user_optional, None)
        
        campanha = setup_data["campanha"]
        alvo = setup_data["alvos"]["whatsapp"]
        
        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
                "canal": "whatsapp",
                "anonimo": True
            }
        )
        assert response.status_code == 401

    def test_criar_acao_com_dados_ativista_por_service_account(self, client, db_session, mock_service_account, setup_data):
        """Service account pode criar ação com dados do ativista"""
        app.dependency_overrides[get_current_user] = lambda: mock_service_account
        
        campanha = setup_data["campanha"]
        alvo = setup_data["alvos"]["email"]
        
        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
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

    def test_criar_acao_com_usuario_logado(self, client, db_session, mock_user, setup_data):
        """Usuário logado tem ativista_id preenchido automaticamente"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        campanha = setup_data["campanha"]
        alvo = setup_data["alvos"]["instagram"]
        
        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
                "canal": "instagram"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["ativista_id"] == "test-user-123"
        assert data["anonimo"] is False
        
        # ✅ Dados do usuário são priorizados, mesmo se enviar dados extras
        alvo = setup_data["alvos"]["email"]
        
        response2 = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
                "canal": "email",
                "ativista": {
                    "nome": "Nome Diferente",
                    "email": "outro@email.com"
                }
            }
        )
        assert response2.status_code == 201
        data2 = response2.json()
        assert data2["ativista_id"] == "test-user-123"  # Dados do token prevalecem

    def test_ativista_anonimo_com_dados_deve_ignorar(self, client, db_session, mock_user, setup_data):
        """Se anonimo=True, dados do ativista são ignorados mesmo para usuário logado"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        campanha = setup_data["campanha"]
        alvo = setup_data["alvos"]["whatsapp"]
        
        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
                "canal": "whatsapp",
                "anonimo": True,
                "ativista": {
                    "nome": "João Silva",
                    "email": "joao@email.com"
                }
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["anonimo"] is True
        assert data["ativista_nome"] is None
        assert data["ativista_email"] is None
        assert data["ativista_id"] is None
        
    def test_criar_acao_nao_anonima_sem_dados_sem_usuario(self, client, db_session, setup_data):
        """Sem usuário logado e sem ativista - deve falhar"""
        app.dependency_overrides.pop(get_current_user, None)
        
        campanha = setup_data["campanha"]
        alvo = setup_data["alvos"]["email"]
        
        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
                "canal": "email",
                "anonimo": False
            }
        )
        # Deve falhar por falta de autenticação OU dados do ativista
        assert response.status_code in [401, 422]