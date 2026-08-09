
import pytest

from pressao_api.core.security import get_current_user
from pressao_api.main import app


class TestAPIValidacoesAcao:
    
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
                raise ValueError(f"Falha ao criar alvo {tipo}: {resp.text}")
            alvos[tipo] = resp.json()
            # Verifica se tem ID
            assert "id" in alvos[tipo], f"Alvo {tipo} sem ID: {alvos[tipo]}"
        
        return {"campanha": campanha, "alvos": alvos}
    
    def test_criar_acao_email_para_alvo_email(self, client, db_session, mock_user, setup_data):
        """Deve permitir email para alvo do tipo email"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        campanha = setup_data["campanha"]
        alvo = setup_data["alvos"]["email"]
        
        assert "id" in alvo, f"Alvo sem ID: {alvo}"
        
        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
                "canal": "email",
                "anonimo": True
            }
        )
        assert response.status_code == 201
    
    def test_criar_acao_email_para_alvo_telefone(self, client, db_session, mock_user, setup_data):
        """Não deve permitir email para alvo do tipo telefone"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        campanha = setup_data["campanha"]
        alvo = setup_data["alvos"]["telefone"]
        
        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
                "canal": "email",
                "anonimo": True
            }
        )
        assert response.status_code == 400
        assert "não é compatível" in response.text
    
    def test_criar_acao_whatsapp_para_alvo_whatsapp(self, client, db_session, mock_user, setup_data):
        """Deve permitir WhatsApp para alvo do tipo whatsapp"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
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
    
    def test_criar_acao_whatsapp_para_alvo_telefone(self, client, db_session, mock_user, setup_data):
        """Não deve permitir WhatsApp para alvo do tipo telefone"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        campanha = setup_data["campanha"]
        alvo = setup_data["alvos"]["telefone"]
        
        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
                "canal": "whatsapp",
                "anonimo": True
            }
        )
        assert response.status_code == 400
        assert "não é compatível" in response.text
    
    def test_criar_acao_telefone_para_alvo_telefone(self, client, db_session, mock_user, setup_data):
        """Deve permitir telefone para alvo do tipo telefone"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        campanha = setup_data["campanha"]
        alvo = setup_data["alvos"]["telefone"]
        
        response = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha["id"],
                "alvo_id": alvo["id"],
                "canal": "telefone",
                "anonimo": True
            }
        )
        assert response.status_code == 201