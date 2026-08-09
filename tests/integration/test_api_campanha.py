import pytest
from uuid import uuid4
from pressao_api.main import app
from pressao_api.core.security import get_current_user

class TestAPICampanha:
    
    def test_criar_campanha_com_admin(self, client, db_session, mock_admin):
        """Admin pode criar campanha"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        response = client.post(
            "/api/v1/campanhas/",
            json={
                "nome": "Campanha Teste API",
                "descricao": "Descrição via API",
                "dominios_permitidos": ["gmail.com", "yahoo.com"],
                "ativa": True
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["nome"] == "Campanha Teste API"
        assert data["id"] is not None
        assert data["dominios_permitidos"] == ["gmail.com", "yahoo.com"]

    def test_criar_campanha_sem_admin(self, client, db_session, mock_user):
        """Usuário comum NÃO pode criar campanha"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        response = client.post(
            "/api/v1/campanhas/",
            json={
                "nome": "Campanha Inválida",
                "descricao": "Não deve ser criada"
            }
        )
        assert response.status_code == 403
        assert "Apenas administradores" in response.text

    def test_criar_campanha_com_nome_duplicado(self, client, db_session, mock_admin):
        """Não permite criar campanha com nome duplicado"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        # Cria a primeira
        client.post(
            "/api/v1/campanhas/",
            json={"nome": "Campanha Duplicada"}
        )
        
        # Tenta criar com mesmo nome
        response = client.post(
            "/api/v1/campanhas/",
            json={"nome": "Campanha Duplicada"}
        )
        assert response.status_code == 400
        assert "Já existe uma campanha com este nome" in response.text

    def test_listar_campanhas(self, client, db_session, mock_user):
        """Lista campanhas (qualquer usuário autenticado)"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        response = client.get("/api/v1/campanhas/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_buscar_campanha_por_id(self, client, db_session, mock_admin):
        """Busca campanha por ID"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        # Cria uma campanha
        create_response = client.post(
            "/api/v1/campanhas/",
            json={"nome": "Campanha Busca"}
        )
        campanha_id = create_response.json()["id"]
        
        # Busca a campanha
        response = client.get(f"/api/v1/campanhas/{campanha_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["nome"] == "Campanha Busca"
        assert data["id"] == campanha_id

    def test_buscar_campanha_inexistente(self, client, db_session, mock_user):
        """Busca campanha inexistente retorna 404"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        response = client.get(f"/api/v1/campanhas/{uuid4()}")
        assert response.status_code == 404

    def test_atualizar_campanha(self, client, db_session, mock_admin):
        """Admin pode atualizar campanha"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        # Cria campanha
        create_response = client.post(
            "/api/v1/campanhas/",
            json={"nome": "Nome Antigo", "ativa": True}
        )
        campanha_id = create_response.json()["id"]
        
        # Atualiza
        response = client.put(
            f"/api/v1/campanhas/{campanha_id}",
            json={"nome": "Nome Novo", "ativa": False}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nome"] == "Nome Novo"
        assert data["ativa"] is False

    def test_deletar_campanha(self, client, db_session, mock_admin):
        """Admin pode deletar campanha"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        
        # Cria campanha
        create_response = client.post(
            "/api/v1/campanhas/",
            json={"nome": "Campanha Deletar"}
        )
        campanha_id = create_response.json()["id"]
        
        # Deleta
        response = client.delete(f"/api/v1/campanhas/{campanha_id}")
        assert response.status_code == 204
        
        # Verifica que não existe mais
        get_response = client.get(f"/api/v1/campanhas/{campanha_id}")
        assert get_response.status_code == 404