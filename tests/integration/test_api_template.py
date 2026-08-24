from uuid import uuid4

import pytest

from pressao_api.core.security import get_current_user
from pressao_api.main import app


class TestAPITemplate:
    @pytest.fixture
    def campanha(self, client, db_session, mock_admin):
        """Cria uma campanha para os testes de template"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin

        response = client.post("/api/v1/campanhas/", json={"nome": "Campanha Templates"})
        return response.json()

    def _payload(self, campanha_id, **overrides):
        payload = {
            "campanha_id": campanha_id,
            "canal": "email",
            "titulo": "Assunto do e-mail",
            "conteudo": "<p>Olá {alvo_nome}</p>",
            "ativo": True,
        }
        payload.update(overrides)
        return payload

    def test_criar_template(self, client, db_session, mock_admin, campanha):
        """Admin cria template para a campanha"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin

        response = client.post("/api/v1/templates/", json=self._payload(campanha["id"]))

        assert response.status_code == 201
        data = response.json()
        assert data["campanha_id"] == campanha["id"]
        assert data["canal"] == "email"
        assert data["titulo"] == "Assunto do e-mail"
        assert data["conteudo"] == "<p>Olá {alvo_nome}</p>"
        assert data["ativo"] is True
        assert "id" in data

    def test_criar_template_exige_admin(self, client, db_session, mock_user, campanha):
        """Ativista comum não pode criar template"""
        campanha_id = campanha["id"]
        app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.post("/api/v1/templates/", json=self._payload(campanha_id))

        assert response.status_code == 403

    def test_criar_template_para_campanha_inexistente(self, client, db_session, mock_admin):
        """Não permite criar template para campanha inexistente"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin

        response = client.post("/api/v1/templates/", json=self._payload(str(uuid4())))

        assert response.status_code == 404
        assert "Campanha não encontrada" in response.text

    def test_criar_template_com_canal_invalido(self, client, db_session, mock_admin, campanha):
        """Canal precisa ser um dos canais suportados"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin

        response = client.post(
            "/api/v1/templates/", json=self._payload(campanha["id"], canal="pombo-correio")
        )

        assert response.status_code == 422

    def test_criar_template_com_conteudo_vazio(self, client, db_session, mock_admin, campanha):
        """Conteúdo é obrigatório"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin

        response = client.post(
            "/api/v1/templates/", json=self._payload(campanha["id"], conteudo="")
        )

        assert response.status_code == 422

    def test_listar_templates_por_campanha(self, client, db_session, mock_admin, campanha):
        """Lista todos os templates da campanha"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        campanha_id = campanha["id"]

        for i in range(3):
            client.post(
                "/api/v1/templates/", json=self._payload(campanha_id, titulo=f"Template {i}")
            )

        response = client.get(f"/api/v1/templates/campanha/{campanha_id}")

        assert response.status_code == 200
        assert len(response.json()) == 3

    def test_listar_templates_filtra_por_canal(self, client, db_session, mock_admin, campanha):
        """Filtro por canal na listagem"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        campanha_id = campanha["id"]

        client.post("/api/v1/templates/", json=self._payload(campanha_id, canal="email"))
        client.post("/api/v1/templates/", json=self._payload(campanha_id, canal="whatsapp"))

        response = client.get(f"/api/v1/templates/campanha/{campanha_id}?canal=email")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["canal"] == "email"

    def test_listar_templates_filtra_por_ativo(self, client, db_session, mock_admin, campanha):
        """Filtro por ativo na listagem"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        campanha_id = campanha["id"]

        client.post("/api/v1/templates/", json=self._payload(campanha_id, titulo="Ativo"))
        client.post(
            "/api/v1/templates/", json=self._payload(campanha_id, titulo="Inativo", ativo=False)
        )

        response = client.get(f"/api/v1/templates/campanha/{campanha_id}?ativo=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["titulo"] == "Ativo"

    def test_listar_templates_permitido_para_ativista(
        self, client, db_session, mock_admin, campanha
    ):
        """Leitura não é restrita a admin"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        campanha_id = campanha["id"]
        client.post("/api/v1/templates/", json=self._payload(campanha_id))

        app.dependency_overrides[get_current_user] = lambda: {
            "id": "user-1",
            "is_admin": False,
            "nome": "Ativista",
            "email": "ativista@email.com",
        }
        response = client.get(f"/api/v1/templates/campanha/{campanha_id}")

        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_obter_template_por_id(self, client, db_session, mock_admin, campanha):
        """Busca template por ID"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        criado = client.post(
            "/api/v1/templates/", json=self._payload(campanha["id"], titulo="Busca")
        ).json()

        response = client.get(f"/api/v1/templates/{criado['id']}")

        assert response.status_code == 200
        assert response.json()["titulo"] == "Busca"

    def test_obter_template_inexistente(self, client, db_session, mock_admin):
        """Template inexistente devolve 404"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin

        response = client.get(f"/api/v1/templates/{uuid4()}")

        assert response.status_code == 404
        assert "Template não encontrado" in response.text

    def test_atualizar_template(self, client, db_session, mock_admin, campanha):
        """Admin atualiza template"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        criado = client.post("/api/v1/templates/", json=self._payload(campanha["id"])).json()

        response = client.put(
            f"/api/v1/templates/{criado['id']}",
            json={"titulo": "Novo assunto", "ativo": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["titulo"] == "Novo assunto"
        assert data["ativo"] is False

    def test_atualizar_template_exige_admin(
        self, client, db_session, mock_admin, mock_user, campanha
    ):
        """Ativista comum não pode atualizar template"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        criado = client.post("/api/v1/templates/", json=self._payload(campanha["id"])).json()

        app.dependency_overrides[get_current_user] = lambda: mock_user
        response = client.put(f"/api/v1/templates/{criado['id']}", json={"titulo": "Hackeado"})

        assert response.status_code == 403

    def test_atualizar_template_inexistente(self, client, db_session, mock_admin):
        """Atualizar template inexistente devolve 404"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin

        response = client.put(f"/api/v1/templates/{uuid4()}", json={"titulo": "Novo"})

        assert response.status_code == 404

    def test_deletar_template(self, client, db_session, mock_admin, campanha):
        """Admin deleta template"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        criado = client.post("/api/v1/templates/", json=self._payload(campanha["id"])).json()

        response = client.delete(f"/api/v1/templates/{criado['id']}")

        assert response.status_code == 204
        assert client.get(f"/api/v1/templates/{criado['id']}").status_code == 404

    def test_deletar_template_exige_admin(
        self, client, db_session, mock_admin, mock_user, campanha
    ):
        """Ativista comum não pode deletar template"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        criado = client.post("/api/v1/templates/", json=self._payload(campanha["id"])).json()

        app.dependency_overrides[get_current_user] = lambda: mock_user
        response = client.delete(f"/api/v1/templates/{criado['id']}")

        assert response.status_code == 403
