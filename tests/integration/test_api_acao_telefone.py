from uuid import uuid4

import pytest

from pressao_api.core.config import settings
from pressao_api.core.security import get_current_user
from pressao_api.main import app


@pytest.fixture
def ativista(client, mock_service_account):
    app.dependency_overrides[get_current_user] = lambda: mock_service_account


def _payload(setup, **extra):
    payload = {
        "campanha_id": setup["campanha"]["id"],
        "alvo_id": setup["agregado"]["id"],
        "canal": "telefone",
        "ativista": {"nome": "Maria", "telefone": "(11) 99999-0000"},
    }
    payload.update(extra)
    return payload


def _criar(client, setup, **extra):
    resp = client.post("/api/v1/acoes/", json=_payload(setup, **extra))
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


def _ligacao(client, acao_id):
    resp = client.get(f"/api/v1/acoes/{acao_id}/ligacao")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _status_acao(client, acao_id):
    return client.get(f"/api/v1/acoes/{acao_id}/status").json()["status"]


def _contador(client, campanha_id):
    return client.get(f"/api/v1/campanhas/{campanha_id}").json()["acoes_confirmadas"]


def _ligacao_id(acao):
    return acao["proximo_passo"]["dados"]["ligacao_id"]


class TestCriarAcaoTelefone:
    def test_cria_acao_multi_alvo_com_alvo_da_vez(self, client, campanha_telefone, ativista):
        data = _criar(client, campanha_telefone)

        assert data["tipo_acao"] == "multi_alvo"
        assert data["status_atual"] == "PROCESSANDO"
        assert data["proximo_passo"]["tipo"] == "WEBHOOK_AGUARDAR"
        assert data["disparos_resumo"]["total"] == 1

        dados = data["proximo_passo"]["dados"]
        ids = {m["id"] for m in campanha_telefone["membros"].values()}
        assert dados["alvo"]["id"] in ids
        assert "contato" not in dados["alvo"]
        assert dados["selecao"] == "automatica"
        assert dados["ligacao_id"]
        assert dados["disparo_id"]
        assert dados["numero_origem_prefixo"] == "11"
        assert dados["dry_run"] is True
        assert dados["alvo"]["nome"] in dados["roteiro"]
        assert "Maria" in dados["roteiro"]
        assert "Campanha Telefone" in dados["roteiro"]

    def test_cria_acao_com_membro_escolhido(self, client, campanha_telefone, ativista):
        membro = campanha_telefone["membros"]["Beltrano Silva"]
        data = _criar(client, campanha_telefone, membro_id=membro["id"])

        dados = data["proximo_passo"]["dados"]
        assert dados["alvo"]["id"] == membro["id"]
        assert dados["alvo"]["cargo"] == "Deputado"
        assert dados["selecao"] == "ativista"

    def test_membro_sugerido_mantem_selecao_automatica(
        self, client, campanha_telefone, ativista
    ):
        membro = campanha_telefone["membros"]["Fulana Souza"]
        data = _criar(client, campanha_telefone, membro_id=membro["id"], selecao="automatica")

        dados = data["proximo_passo"]["dados"]
        assert dados["alvo"]["id"] == membro["id"]
        assert dados["selecao"] == "automatica"
        assert _ligacao(client, data["acao_id"])["selecao"] == "automatica"

    def test_selecao_explicita_de_ativista(self, client, campanha_telefone, ativista):
        membro = campanha_telefone["membros"]["Fulana Souza"]
        data = _criar(client, campanha_telefone, membro_id=membro["id"], selecao="ativista")

        assert data["proximo_passo"]["dados"]["selecao"] == "ativista"

    def test_selecao_automatica_sem_membro_usa_alvo_da_vez(
        self, client, campanha_telefone, ativista
    ):
        data = _criar(client, campanha_telefone, selecao="automatica")

        assert data["proximo_passo"]["dados"]["selecao"] == "automatica"

    def test_recusa_selecao_invalida(self, client, campanha_telefone, ativista):
        resp = client.post("/api/v1/acoes/", json=_payload(campanha_telefone, selecao="outra"))

        assert resp.status_code == 422

    def test_recusa_membro_de_fora_do_agregado(self, client, campanha_telefone, ativista):
        resp = client.post(
            "/api/v1/acoes/", json=_payload(campanha_telefone, membro_id=str(uuid4()))
        )
        assert resp.status_code == 400
        assert "não pertence" in resp.text

    def test_recusa_membro_id_fora_do_canal_telefone(
        self, client, mock_admin, campanha_telefone, ativista
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
        email = next(a for a in alvos if a["tipo_contato"] == "email")

        resp = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha_id,
                "alvo_id": email["id"],
                "canal": "email",
                "membro_id": campanha_telefone["membros"]["Ciclana de Tal"]["id"],
                "ativista": {"nome": "Maria", "email": "maria@email.com"},
            },
        )
        assert resp.status_code == 400
        assert "membro_id" in resp.text

    def test_exige_telefone_do_ativista(self, client, campanha_telefone, ativista):
        resp = client.post(
            "/api/v1/acoes/",
            json=_payload(
                campanha_telefone, ativista={"nome": "Maria", "email": "maria@email.com"}
            ),
        )
        assert resp.status_code == 400
        assert "telefone do ativista" in resp.text

    def test_exige_numero_de_origem_fora_do_dry_run(
        self, client, mock_admin, mock_service_account, campanha_telefone, monkeypatch
    ):
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        campanha = client.post("/api/v1/campanhas/", json={"nome": "Sem Número"}).json()
        client.post(
            "/api/v1/alvos/",
            json={
                "nome": "Alvo",
                "contato": "11977776666",
                "tipo_contato": "telefone",
                "campanha_id": campanha["id"],
            },
        )
        agregado = client.get(f"/api/v1/alvos/campanha/{campanha['id']}").json()[0]

        monkeypatch.setattr(settings, "TWILIO_SANDBOX_MODE", False)
        monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC123")
        monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "token-real")
        app.dependency_overrides[get_current_user] = lambda: mock_service_account
        resp = client.post(
            "/api/v1/acoes/",
            json=_payload({"campanha": campanha, "agregado": agregado}),
        )
        assert resp.status_code == 400
        assert "número de origem" in resp.text

    def test_falha_do_provedor_marca_acao_como_falha(
        self, client, campanha_telefone, ativista, monkeypatch
    ):
        from twilio.base.exceptions import TwilioRestException

        from pressao_api.services.telefone_service import telefone_service

        def _cliente_que_recusa():
            raise TwilioRestException(status=400, uri="/Calls", msg="Recusado", code=21211)

        monkeypatch.setattr(settings, "TWILIO_SANDBOX_MODE", False)
        monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC123")
        monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "token-real")
        monkeypatch.setattr(telefone_service, "_cliente", _cliente_que_recusa)

        data = _criar(client, campanha_telefone)
        assert data["status_atual"] == "FALHA"
        assert data["disparos_resumo"]["falhas"] == 1

        ligacao = _ligacao(client, data["acao_id"])
        assert ligacao["etapa"] == "FALHA"
        assert ligacao["motivo_falha"] == "erro_provedor"

    def test_status_inicial_da_ligacao(self, client, campanha_telefone, ativista):
        data = _criar(client, campanha_telefone)
        ligacao = _ligacao(client, data["acao_id"])

        assert ligacao["ligacao_id"] == _ligacao_id(data)
        assert ligacao["etapa"] == "INICIANDO"
        assert ligacao["tentativas"] == 1
        assert ligacao["acao_status"] == "PROCESSANDO"
        assert ligacao["origem_falha"] is None
        assert ligacao["alvo"]["nome"] == data["proximo_passo"]["dados"]["alvo"]["nome"]

    def test_acao_sem_ligacao(self, client, campanha_telefone, ativista):
        resp = client.get(f"/api/v1/acoes/{uuid4()}/ligacao")
        assert resp.status_code == 404


class TestEventosLigacao:
    def test_fluxo_completo_conclui_acao_e_incrementa_contador(
        self, client, campanha_telefone, ativista
    ):
        campanha_id = campanha_telefone["campanha"]["id"]
        data = _criar(client, campanha_telefone)
        ligacao_id = _ligacao_id(data)

        _simular(client, ligacao_id, "ativista", "ringing")
        assert _ligacao(client, data["acao_id"])["etapa"] == "CHAMANDO_ATIVISTA"

        _simular(client, ligacao_id, "ativista", "in-progress")
        assert _ligacao(client, data["acao_id"])["etapa"] == "CHAMANDO_ALVO"

        _simular(client, ligacao_id, "alvo", "ringing")
        assert _ligacao(client, data["acao_id"])["etapa"] == "CHAMANDO_ALVO"

        _simular(client, ligacao_id, "alvo", "in-progress")
        assert _ligacao(client, data["acao_id"])["etapa"] == "EM_ANDAMENTO"

        resultado = _simular(client, ligacao_id, "alvo", "completed", duracao_seg=42)
        assert resultado["resultado"] == "processado"

        ligacao = _ligacao(client, data["acao_id"])
        assert ligacao["etapa"] == "CONCLUIDA"
        assert ligacao["duracao_seg"] == 42
        assert ligacao["acao_status"] == "CONCLUIDA"
        assert _status_acao(client, data["acao_id"]) == "CONCLUIDA"
        assert _contador(client, campanha_id) == 1

    def test_evento_repetido_nao_incrementa_de_novo(self, client, campanha_telefone, ativista):
        campanha_id = campanha_telefone["campanha"]["id"]
        data = _criar(client, campanha_telefone)
        ligacao_id = _ligacao_id(data)

        _simular(client, ligacao_id, "alvo", "in-progress")
        _simular(client, ligacao_id, "alvo", "completed", duracao_seg=30)
        repetido = _simular(client, ligacao_id, "alvo", "completed", duracao_seg=30)

        assert repetido["resultado"] == "ignorado"
        assert _contador(client, campanha_id) == 1

    @pytest.mark.parametrize(
        ("perna", "status", "origem", "motivo"),
        [
            ("ativista", "no-answer", "ativista", "no-answer"),
            ("ativista", "busy", "ativista", "no-answer"),
            ("ativista", "failed", "ativista", "failed"),
            ("ativista", "canceled", "ativista", "canceled"),
            ("alvo", "no-answer", "alvo", "no-answer"),
            ("alvo", "busy", "alvo", "busy"),
            ("alvo", "failed", "alvo", "failed"),
            ("alvo", "canceled", "ativista", "canceled"),
        ],
    )
    def test_falhas_por_perna(
        self, client, campanha_telefone, ativista, perna, status, origem, motivo
    ):
        campanha_id = campanha_telefone["campanha"]["id"]
        data = _criar(client, campanha_telefone)

        _simular(client, _ligacao_id(data), perna, status)

        ligacao = _ligacao(client, data["acao_id"])
        assert ligacao["etapa"] == "FALHA"
        assert ligacao["origem_falha"] == origem
        assert ligacao["motivo_falha"] == motivo
        assert _status_acao(client, data["acao_id"]) == "FALHA"
        assert _contador(client, campanha_id) == 0

    def test_ativista_desliga_antes_do_alvo_atender(self, client, campanha_telefone, ativista):
        data = _criar(client, campanha_telefone)
        ligacao_id = _ligacao_id(data)

        _simular(client, ligacao_id, "ativista", "in-progress")
        _simular(client, ligacao_id, "ativista", "completed", duracao_seg=8)

        ligacao = _ligacao(client, data["acao_id"])
        assert ligacao["origem_falha"] == "ativista"
        assert ligacao["motivo_falha"] == "canceled"

    def test_alvo_encerra_sem_atender(self, client, campanha_telefone, ativista):
        data = _criar(client, campanha_telefone)
        _simular(client, _ligacao_id(data), "alvo", "completed")

        ligacao = _ligacao(client, data["acao_id"])
        assert ligacao["origem_falha"] == "alvo"
        assert ligacao["motivo_falha"] == "no-answer"

    def test_ativista_encerra_depois_do_alvo_atender_conclui(
        self, client, campanha_telefone, ativista
    ):
        data = _criar(client, campanha_telefone)
        ligacao_id = _ligacao_id(data)

        _simular(client, ligacao_id, "alvo", "in-progress")
        _simular(client, ligacao_id, "ativista", "completed", duracao_seg=60)

        assert _ligacao(client, data["acao_id"])["etapa"] == "CONCLUIDA"

    def test_ligacao_inexistente(self, client, campanha_telefone):
        resp = client.post(
            "/api/v1/webhooks/telefone/simular",
            json={"ligacao_id": str(uuid4()), "perna": "ativista", "status": "ringing"},
        )
        assert resp.status_code == 404

    def test_simulacao_desabilitada_em_producao(
        self, client, campanha_telefone, ativista, monkeypatch
    ):
        data = _criar(client, campanha_telefone)
        monkeypatch.setattr(settings, "APP_ENV", "production")

        resp = client.post(
            "/api/v1/webhooks/telefone/simular",
            json={"ligacao_id": _ligacao_id(data), "perna": "ativista", "status": "ringing"},
        )
        assert resp.status_code == 404


class TestNovaTentativa:
    def test_nova_tentativa_reabre_acao_com_novo_disparo(
        self, client, campanha_telefone, ativista
    ):
        data = _criar(client, campanha_telefone)
        _simular(client, _ligacao_id(data), "ativista", "no-answer")

        resp = client.post(
            f"/api/v1/acoes/{data['acao_id']}/ligacoes",
            json={"telefone": "(21) 98888-7777"},
        )
        assert resp.status_code == 201, resp.text
        nova = resp.json()

        assert nova["acao_id"] == data["acao_id"]
        assert nova["status_atual"] == "PROCESSANDO"
        assert nova["ativista_telefone"] == "+5521988887777"
        assert nova["disparos_resumo"]["total"] == 2
        assert _ligacao_id(nova) != _ligacao_id(data)

        ligacao = _ligacao(client, data["acao_id"])
        assert ligacao["ligacao_id"] == _ligacao_id(nova)
        assert ligacao["tentativas"] == 2
        assert ligacao["etapa"] == "INICIANDO"

    def test_nova_tentativa_com_membro_escolhido(self, client, campanha_telefone, ativista):
        data = _criar(client, campanha_telefone)
        _simular(client, _ligacao_id(data), "alvo", "busy")
        membro = campanha_telefone["membros"]["Fulana Souza"]

        resp = client.post(
            f"/api/v1/acoes/{data['acao_id']}/ligacoes", json={"membro_id": membro["id"]}
        )
        assert resp.status_code == 201
        assert resp.json()["proximo_passo"]["dados"]["alvo"]["id"] == membro["id"]
        assert resp.json()["proximo_passo"]["dados"]["selecao"] == "ativista"

    def test_conclusao_apos_nova_tentativa_conta_uma_vez(
        self, client, campanha_telefone, ativista
    ):
        campanha_id = campanha_telefone["campanha"]["id"]
        data = _criar(client, campanha_telefone)
        _simular(client, _ligacao_id(data), "alvo", "no-answer")

        nova = client.post(f"/api/v1/acoes/{data['acao_id']}/ligacoes", json={}).json()
        _simular(client, _ligacao_id(nova), "alvo", "in-progress")
        _simular(client, _ligacao_id(nova), "alvo", "completed", duracao_seg=50)

        assert _status_acao(client, data["acao_id"]) == "CONCLUIDA"
        assert _contador(client, campanha_id) == 1

    def test_bloqueia_com_ligacao_ativa(self, client, campanha_telefone, ativista):
        data = _criar(client, campanha_telefone)

        resp = client.post(f"/api/v1/acoes/{data['acao_id']}/ligacoes", json={})
        assert resp.status_code == 409

    def test_bloqueia_acao_concluida(self, client, campanha_telefone, ativista):
        data = _criar(client, campanha_telefone)
        _simular(client, _ligacao_id(data), "alvo", "in-progress")
        _simular(client, _ligacao_id(data), "alvo", "completed", duracao_seg=20)

        resp = client.post(f"/api/v1/acoes/{data['acao_id']}/ligacoes", json={})
        assert resp.status_code == 400
        assert "concluída" in resp.text

    def test_recusa_acao_de_outro_canal(self, client, mock_admin, campanha_telefone, ativista):
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        campanha_id = campanha_telefone["campanha"]["id"]
        insta = client.post(
            "/api/v1/alvos/",
            json={
                "nome": "Perfil",
                "contato": "https://instagram.com/p/abc",
                "tipo_contato": "instagram",
                "campanha_id": campanha_id,
            },
        ).json()
        acao = client.post(
            "/api/v1/acoes/",
            json={
                "campanha_id": campanha_id,
                "alvo_id": insta["id"],
                "canal": "instagram",
                "anonimo": True,
            },
        ).json()

        resp = client.post(f"/api/v1/acoes/{acao['acao_id']}/ligacoes", json={})
        assert resp.status_code == 400

    def test_recusa_telefone_invalido(self, client, campanha_telefone, ativista):
        data = _criar(client, campanha_telefone)
        _simular(client, _ligacao_id(data), "ativista", "failed")

        resp = client.post(f"/api/v1/acoes/{data['acao_id']}/ligacoes", json={"telefone": "123"})
        assert resp.status_code == 422

    def test_acao_inexistente(self, client, campanha_telefone, ativista):
        resp = client.post(f"/api/v1/acoes/{uuid4()}/ligacoes", json={})
        assert resp.status_code == 404
