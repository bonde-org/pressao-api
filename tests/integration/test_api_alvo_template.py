import pytest

from pressao_api.core.security import get_current_user
from pressao_api.main import app


class TestAlvoComTemplateSorteado:
    @pytest.fixture
    def campanha(self, client, db_session, mock_admin):
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        return client.post("/api/v1/campanhas/", json={"nome": "Campanha Sorteio"}).json()

    def _criar_alvo(self, client, campanha_id, nome, contato, tipo_contato):
        return client.post(
            "/api/v1/alvos/",
            json={
                "nome": nome,
                "contato": contato,
                "tipo_contato": tipo_contato,
                "campanha_id": campanha_id,
            },
        ).json()

    def _criar_template(self, client, campanha_id, titulo, canal="email", ativo=True):
        return client.post(
            "/api/v1/templates/",
            json={
                "campanha_id": campanha_id,
                "canal": canal,
                "titulo": titulo,
                "conteudo": f"<p>{titulo}</p>",
                "ativo": ativo,
            },
        ).json()

    def test_alvo_de_email_recebe_template_sorteado(self, client, db_session, mock_admin, campanha):
        """Alvo de e-mail traz o template sorteado na listagem"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        campanha_id = campanha["id"]
        self._criar_alvo(client, campanha_id, "Alvo Email", "alvo@email.com", "email")
        template = self._criar_template(client, campanha_id, "Assunto único")

        response = client.get(f"/api/v1/alvos/campanha/{campanha_id}")

        assert response.status_code == 200
        alvo = response.json()[0]
        assert alvo["template"] is not None
        assert alvo["template"]["id"] == template["id"]
        assert alvo["template"]["titulo"] == "Assunto único"
        assert alvo["template"]["conteudo"] == "<p>Assunto único</p>"
        assert alvo["template"]["canal"] == "email"

    def test_alvo_de_outro_canal_nao_recebe_template(
        self, client, db_session, mock_admin, campanha
    ):
        """Somente alvos de e-mail recebem template"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        campanha_id = campanha["id"]
        self._criar_alvo(client, campanha_id, "Alvo Insta", "@perfil", "instagram")
        self._criar_template(client, campanha_id, "Assunto único")

        response = client.get(f"/api/v1/alvos/campanha/{campanha_id}")

        assert response.status_code == 200
        assert response.json()[0]["template"] is None

    def test_campanha_sem_templates_devolve_template_nulo(
        self, client, db_session, mock_admin, campanha
    ):
        """Sem templates cadastrados a listagem continua funcionando"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        campanha_id = campanha["id"]
        self._criar_alvo(client, campanha_id, "Alvo Email", "alvo@email.com", "email")

        response = client.get(f"/api/v1/alvos/campanha/{campanha_id}")

        assert response.status_code == 200
        assert response.json()[0]["template"] is None

    def test_template_inativo_nao_e_sorteado(self, client, db_session, mock_admin, campanha):
        """Template inativo é ignorado no sorteio"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        campanha_id = campanha["id"]
        self._criar_alvo(client, campanha_id, "Alvo Email", "alvo@email.com", "email")
        self._criar_template(client, campanha_id, "Inativo", ativo=False)

        response = client.get(f"/api/v1/alvos/campanha/{campanha_id}")

        assert response.status_code == 200
        assert response.json()[0]["template"] is None

    def test_template_de_outro_canal_nao_e_sorteado(self, client, db_session, mock_admin, campanha):
        """Template de outro canal não é sorteado para alvo de e-mail"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        campanha_id = campanha["id"]
        self._criar_alvo(client, campanha_id, "Alvo Email", "alvo@email.com", "email")
        self._criar_template(client, campanha_id, "WhatsApp", canal="whatsapp")

        response = client.get(f"/api/v1/alvos/campanha/{campanha_id}")

        assert response.status_code == 200
        assert response.json()[0]["template"] is None

    def test_sorteio_usa_apenas_templates_da_campanha(
        self, client, db_session, mock_admin, campanha
    ):
        """Template de outra campanha nunca é sorteado"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        campanha_id = campanha["id"]
        outra = client.post("/api/v1/campanhas/", json={"nome": "Outra Campanha"}).json()
        self._criar_alvo(client, campanha_id, "Alvo Email", "alvo@email.com", "email")
        self._criar_template(client, outra["id"], "Da outra campanha")

        response = client.get(f"/api/v1/alvos/campanha/{campanha_id}")

        assert response.status_code == 200
        assert response.json()[0]["template"] is None

    def test_sorteio_cobre_mais_de_um_template_entre_requests(
        self, client, db_session, mock_admin, campanha
    ):
        """Com vários templates ativos, requests sucessivos variam o sorteado"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        campanha_id = campanha["id"]
        self._criar_alvo(client, campanha_id, "Alvo Email", "alvo@email.com", "email")
        for i in range(4):
            self._criar_template(client, campanha_id, f"Assunto {i}")

        sorteados = set()
        for _ in range(40):
            response = client.get(f"/api/v1/alvos/campanha/{campanha_id}")
            sorteados.add(response.json()[0]["template"]["id"])

        assert len(sorteados) > 1

    def test_obter_alvo_por_id_tambem_traz_template(self, client, db_session, mock_admin, campanha):
        """Detalhe do alvo também traz o template sorteado"""
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        campanha_id = campanha["id"]
        alvo = self._criar_alvo(client, campanha_id, "Alvo Email", "alvo@email.com", "email")
        template = self._criar_template(client, campanha_id, "Assunto único")

        response = client.get(f"/api/v1/alvos/{alvo['id']}")

        assert response.status_code == 200
        assert response.json()["template"]["id"] == template["id"]
