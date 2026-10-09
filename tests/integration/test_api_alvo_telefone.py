from uuid import uuid4

from pressao_api.core.security import get_current_user
from pressao_api.main import app


def _criar_acao(client, campanha_id, agregado_id, membro_id=None):
    payload = {
        "campanha_id": campanha_id,
        "alvo_id": agregado_id,
        "canal": "telefone",
        "ativista": {"nome": "Ativista", "telefone": "11999990000"},
    }
    if membro_id:
        payload["membro_id"] = membro_id
    resp = client.post("/api/v1/acoes/", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _simular(client, ligacao_id, perna, status, duracao_seg=None):
    resp = client.post(
        "/api/v1/webhooks/telefone/simular",
        json={
            "ligacao_id": ligacao_id,
            "perna": perna,
            "status": status,
            "duracao_seg": duracao_seg,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestListagemAgregadoTelefone:
    def test_lista_agregado_de_telefone_e_oculta_individuais(
        self, client, campanha_telefone
    ):
        campanha_id = campanha_telefone["campanha"]["id"]
        alvos = client.get(f"/api/v1/alvos/campanha/{campanha_id}").json()

        assert len(alvos) == 1
        agregado = alvos[0]
        assert agregado["modo"] == "agregado"
        assert agregado["tipo_contato"] == "telefone"
        assert agregado["nome"] == "Pressionar por Telefone"
        assert agregado["total_membros"] == 3
        assert agregado["template"]["canal"] == "telefone"

    def test_membros_publicos_sem_contato_em_ordem_alfabetica(
        self, client, campanha_telefone
    ):
        agregado = campanha_telefone["agregado"]
        membros = agregado["membros"]

        assert [m["nome"] for m in membros] == [
            "Beltrano Silva",
            "Ciclana de Tal",
            "Fulana Souza",
        ]
        ciclana = membros[1]
        assert ciclana["id"] == campanha_telefone["membros"]["Ciclana de Tal"]["id"]
        assert ciclana["cargo"] == "Vereador"
        assert ciclana["partido"] == "PT"
        assert all("contato" not in m for m in membros)

    def test_agregados_de_email_e_telefone_convivem(
        self, client, mock_admin, campanha_telefone
    ):
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        campanha_id = campanha_telefone["campanha"]["id"]
        client.post(
            "/api/v1/alvos/",
            json={
                "nome": "Gabinete",
                "contato": "gabinete@email.com",
                "tipo_contato": "email",
                "campanha_id": campanha_id,
            },
        )

        alvos = client.get(f"/api/v1/alvos/campanha/{campanha_id}").json()
        tipos = sorted((a["tipo_contato"], a["modo"]) for a in alvos)
        assert tipos == [("email", "agregado"), ("telefone", "agregado")]
        email = next(a for a in alvos if a["tipo_contato"] == "email")
        assert email["membros"] == [{"nome": "Gabinete"}]

    def test_alvo_inativo_sai_dos_membros(self, client, mock_admin, campanha_telefone):
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        campanha_id = campanha_telefone["campanha"]["id"]
        membro = campanha_telefone["membros"]["Fulana Souza"]

        client.put(f"/api/v1/alvos/{membro['id']}", json={"ativo": False})

        alvos = client.get(f"/api/v1/alvos/campanha/{campanha_id}").json()
        assert alvos[0]["total_membros"] == 2
        assert "Fulana Souza" not in [m["nome"] for m in alvos[0]["membros"]]

    def test_obter_agregado_por_id_traz_membros_e_roteiro(self, client, campanha_telefone):
        agregado = campanha_telefone["agregado"]
        data = client.get(f"/api/v1/alvos/{agregado['id']}").json()
        assert data["total_membros"] == 3
        assert data["membros"][0]["id"]
        assert data["template"]["canal"] == "telefone"


class TestProximoMembro:
    def test_retorna_membro_e_roteiro(self, client, campanha_telefone):
        agregado = campanha_telefone["agregado"]
        resp = client.get(f"/api/v1/alvos/{agregado['id']}/proximo-membro")

        assert resp.status_code == 200
        data = resp.json()
        ids = {m["id"] for m in campanha_telefone["membros"].values()}
        assert data["membro"]["id"] in ids
        assert "contato" not in data["membro"]
        assert data["template"]["canal"] == "telefone"

    def test_equilibra_pelo_membro_com_menos_ligacoes(
        self, client, mock_service_account, campanha_telefone
    ):
        campanha_id = campanha_telefone["campanha"]["id"]
        agregado = campanha_telefone["agregado"]
        membros = campanha_telefone["membros"]

        app.dependency_overrides[get_current_user] = lambda: mock_service_account
        _criar_acao(client, campanha_id, agregado["id"], membros["Ciclana de Tal"]["id"])
        _criar_acao(client, campanha_id, agregado["id"], membros["Beltrano Silva"]["id"])

        for _ in range(5):
            data = client.get(f"/api/v1/alvos/{agregado['id']}/proximo-membro").json()
            assert data["membro"]["id"] == membros["Fulana Souza"]["id"]

    def test_falha_do_ativista_nao_conta_para_o_equilibrio(
        self, client, mock_service_account, campanha_telefone
    ):
        campanha_id = campanha_telefone["campanha"]["id"]
        agregado = campanha_telefone["agregado"]
        membros = campanha_telefone["membros"]

        app.dependency_overrides[get_current_user] = lambda: mock_service_account
        acao = _criar_acao(client, campanha_id, agregado["id"], membros["Ciclana de Tal"]["id"])
        _simular(client, acao["proximo_passo"]["dados"]["ligacao_id"], "ativista", "no-answer")
        _criar_acao(client, campanha_id, agregado["id"], membros["Beltrano Silva"]["id"])
        _criar_acao(client, campanha_id, agregado["id"], membros["Fulana Souza"]["id"])

        data = client.get(f"/api/v1/alvos/{agregado['id']}/proximo-membro").json()
        assert data["membro"]["id"] == membros["Ciclana de Tal"]["id"]

    def test_recusa_alvo_que_nao_e_agregado_de_telefone(
        self, client, campanha_telefone
    ):
        membro = campanha_telefone["membros"]["Ciclana de Tal"]
        resp = client.get(f"/api/v1/alvos/{membro['id']}/proximo-membro")
        assert resp.status_code == 400

    def test_alvo_inexistente(self, client, campanha_telefone):
        resp = client.get(f"/api/v1/alvos/{uuid4()}/proximo-membro")
        assert resp.status_code == 404

    def test_sem_membros_ativos(self, client, mock_admin, campanha_telefone):
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        agregado = campanha_telefone["agregado"]
        for membro in campanha_telefone["membros"].values():
            client.put(f"/api/v1/alvos/{membro['id']}", json={"ativo": False})

        resp = client.get(f"/api/v1/alvos/{agregado['id']}/proximo-membro")
        assert resp.status_code == 404
