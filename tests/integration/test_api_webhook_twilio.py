import uuid
import xml.etree.ElementTree as ET

import pytest
from twilio.request_validator import RequestValidator

from pressao_api.core.config import settings
from pressao_api.core.security import get_current_user
from pressao_api.main import app

BASE = "https://teste.exemplo/api/v1/webhooks/twilio"
ROTA = "/api/v1/webhooks/twilio"


@pytest.fixture
def ativista(client, mock_service_account):
    app.dependency_overrides[get_current_user] = lambda: mock_service_account


@pytest.fixture
def acao(client, campanha_telefone, ativista):
    membro = campanha_telefone["membros"]["Beltrano Silva"]
    resp = client.post(
        "/api/v1/acoes/",
        json={
            "campanha_id": campanha_telefone["campanha"]["id"],
            "alvo_id": campanha_telefone["agregado"]["id"],
            "canal": "telefone",
            "membro_id": membro["id"],
            "ativista": {"nome": "Maria", "telefone": "(11) 99999-0000"},
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {
        "acao_id": data["acao_id"],
        "ligacao_id": data["proximo_passo"]["dados"]["ligacao_id"],
        "membro": membro,
        "campanha": campanha_telefone["campanha"],
    }


def _ligacao(client, acao_id):
    resp = client.get(f"/api/v1/acoes/{acao_id}/ligacao")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _status(client, ligacao_id, perna, **params):
    return client.post(f"{ROTA}/status/{ligacao_id}/{perna}", data=params)


class TestTwiml:
    def test_pede_confirmacao_ao_ativista(self, client, acao):
        resp = client.post(f"{ROTA}/twiml/{acao['ligacao_id']}", data={"CallSid": "CA1"})

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/xml")
        gather = ET.fromstring(resp.text).find("Gather")
        assert gather.get("action") == f"{BASE}/conectar/{acao['ligacao_id']}"
        texto = gather.find("Say").text
        assert "Beltrano Silva" in texto
        assert "Campanha Telefone" in texto

    def test_ligacao_inexistente_desliga(self, client):
        resp = client.post(f"{ROTA}/twiml/{uuid.uuid4()}", data={})
        assert resp.status_code == 200
        assert ET.fromstring(resp.text).find("Hangup") is not None

    def test_ligacao_terminal_desliga(self, client, acao):
        _status(client, acao["ligacao_id"], "ativista", CallStatus="no-answer")
        resp = client.post(f"{ROTA}/twiml/{acao['ligacao_id']}", data={})
        assert ET.fromstring(resp.text).find("Hangup") is not None


class TestConectar:
    def test_digito_1_disca_para_o_alvo(self, client, acao):
        resp = client.post(f"{ROTA}/conectar/{acao['ligacao_id']}", data={"Digits": "1"})

        assert resp.status_code == 200
        dial = ET.fromstring(resp.text).find("Dial")
        assert dial.get("callerId") == "+551140028922"
        numero = dial.find("Number")
        assert numero.text == "+5511988880002"
        assert numero.get("statusCallback") == f"{BASE}/status/{acao['ligacao_id']}/alvo"

    @pytest.mark.parametrize("digitos", ["", "2"])
    def test_sem_confirmacao_falha_como_nao_atendida(self, client, acao, digitos):
        resp = client.post(f"{ROTA}/conectar/{acao['ligacao_id']}", data={"Digits": digitos})

        raiz = ET.fromstring(resp.text)
        assert raiz.find("Dial") is None
        assert raiz.find("Hangup") is not None
        ligacao = _ligacao(client, acao["acao_id"])
        assert ligacao["etapa"] == "FALHA"
        assert ligacao["origem_falha"] == "ativista"
        assert ligacao["motivo_falha"] == "no-answer"
        assert ligacao["acao_status"] == "FALHA"

        depois = _status(client, acao["ligacao_id"], "ativista", CallStatus="completed")
        assert depois.status_code == 204
        assert _ligacao(client, acao["acao_id"])["motivo_falha"] == "no-answer"

    def test_ligacao_terminal_nao_disca(self, client, acao):
        _status(client, acao["ligacao_id"], "ativista", CallStatus="busy")
        resp = client.post(f"{ROTA}/conectar/{acao['ligacao_id']}", data={"Digits": "1"})
        raiz = ET.fromstring(resp.text)
        assert raiz.find("Dial") is None
        assert raiz.find("Hangup") is not None


class TestStatus:
    def test_fluxo_real_conclui_e_incrementa_contador(self, client, acao):
        ligacao_id = acao["ligacao_id"]
        campanha_id = acao["campanha"]["id"]
        antes = client.get(f"/api/v1/campanhas/{campanha_id}").json()["acoes_confirmadas"]

        assert _status(client, ligacao_id, "ativista", CallStatus="ringing").status_code == 204
        assert _ligacao(client, acao["acao_id"])["etapa"] == "CHAMANDO_ATIVISTA"
        _status(client, ligacao_id, "ativista", CallStatus="in-progress")
        assert _ligacao(client, acao["acao_id"])["etapa"] == "CHAMANDO_ALVO"
        _status(client, ligacao_id, "alvo", CallStatus="ringing", CallSid="CA2")
        _status(client, ligacao_id, "alvo", CallStatus="in-progress", CallSid="CA2")
        assert _ligacao(client, acao["acao_id"])["etapa"] == "EM_ANDAMENTO"
        _status(
            client, ligacao_id, "alvo", CallStatus="completed", CallDuration="61", CallSid="CA2"
        )

        ligacao = _ligacao(client, acao["acao_id"])
        assert ligacao["etapa"] == "CONCLUIDA"
        assert ligacao["duracao_seg"] == 61
        assert ligacao["acao_status"] == "CONCLUIDA"
        depois = client.get(f"/api/v1/campanhas/{campanha_id}").json()["acoes_confirmadas"]
        assert depois == antes + 1

    def test_alvo_ocupado(self, client, acao):
        _status(client, acao["ligacao_id"], "ativista", CallStatus="in-progress")
        _status(client, acao["ligacao_id"], "alvo", CallStatus="busy")
        ligacao = _ligacao(client, acao["acao_id"])
        assert ligacao["origem_falha"] == "alvo"
        assert ligacao["motivo_falha"] == "busy"

    @pytest.mark.parametrize(
        ("status_alvo", "origem", "motivo"),
        [
            ("no-answer", "alvo", "no-answer"),
            ("busy", "alvo", "busy"),
            ("canceled", "ativista", "canceled"),
        ],
    )
    def test_fim_do_ativista_antes_do_status_do_alvo_espera_o_alvo(
        self, client, acao, status_alvo, origem, motivo
    ):
        ligacao_id = acao["ligacao_id"]
        _status(client, ligacao_id, "ativista", CallStatus="in-progress")
        _status(client, ligacao_id, "alvo", CallStatus="ringing", CallSid="CA2")
        _status(client, ligacao_id, "ativista", CallStatus="completed", CallDuration="30")
        assert _ligacao(client, acao["acao_id"])["etapa"] == "CHAMANDO_ALVO"

        _status(client, ligacao_id, "alvo", CallStatus=status_alvo, CallSid="CA2")

        ligacao = _ligacao(client, acao["acao_id"])
        assert ligacao["etapa"] == "FALHA"
        assert ligacao["origem_falha"] == origem
        assert ligacao["motivo_falha"] == motivo
        assert ligacao["acao_status"] == "FALHA"

    def test_status_desconhecido_e_ignorado(self, client, acao):
        resp = _status(client, acao["ligacao_id"], "ativista", CallStatus="desconhecido")
        assert resp.status_code == 204
        assert _ligacao(client, acao["acao_id"])["etapa"] == "INICIANDO"

    def test_ligacao_inexistente_responde_204(self, client):
        assert _status(client, uuid.uuid4(), "ativista", CallStatus="ringing").status_code == 204

    def test_perna_invalida(self, client, acao):
        resp = _status(client, acao["ligacao_id"], "outra", CallStatus="ringing")
        assert resp.status_code == 422


class TestAssinatura:
    def test_assinatura_invalida_retorna_403(self, client, acao, monkeypatch):
        monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "token-real")
        resp = client.post(
            f"{ROTA}/status/{acao['ligacao_id']}/ativista",
            data={"CallStatus": "ringing"},
            headers={"X-Twilio-Signature": "invalida"},
        )
        assert resp.status_code == 403
        assert _ligacao(client, acao["acao_id"])["etapa"] == "INICIANDO"

    def test_assinatura_sobre_a_url_publica_e_aceita(self, client, acao, monkeypatch):
        monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "token-real")
        params = {"CallStatus": "ringing", "CallSid": "CA1"}
        url = f"{BASE}/status/{acao['ligacao_id']}/ativista"
        assinatura = RequestValidator("token-real").compute_signature(url, params)

        resp = client.post(
            f"{ROTA}/status/{acao['ligacao_id']}/ativista",
            data=params,
            headers={"X-Twilio-Signature": assinatura},
        )
        assert resp.status_code == 204
        assert _ligacao(client, acao["acao_id"])["etapa"] == "CHAMANDO_ATIVISTA"

    def test_twiml_com_assinatura_invalida_retorna_403(self, client, acao, monkeypatch):
        monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "token-real")
        resp = client.post(
            f"{ROTA}/twiml/{acao['ligacao_id']}",
            data={},
            headers={"X-Twilio-Signature": "invalida"},
        )
        assert resp.status_code == 403
