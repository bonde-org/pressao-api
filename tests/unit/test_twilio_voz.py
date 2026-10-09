import uuid
import xml.etree.ElementTree as ET

import pytest
from twilio.request_validator import RequestValidator

from pressao_api.core.config import settings
from pressao_api.schemas.telefone import PernaLigacaoEnum, StatusChamadaEnum
from pressao_api.services import twilio_voz

BASE = "https://teste.exemplo/api/v1/webhooks/twilio"


def _xml(texto: str) -> ET.Element:
    return ET.fromstring(texto)


class TestUrlPublica:
    def test_monta_a_partir_da_base_sem_barra_duplicada(self, monkeypatch):
        monkeypatch.setattr(settings, "TWILIO_WEBHOOK_URL", f"{BASE}/")
        assert twilio_voz.url_publica("/status/x/alvo") == f"{BASE}/status/x/alvo"


class TestAssinatura:
    def _assinar(self, url, params, token="token-real"):
        return RequestValidator(token).compute_signature(url, params)

    def test_aceita_assinatura_valida(self, monkeypatch):
        monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "token-real")
        url = f"{BASE}/status/abc/ativista"
        params = {"CallStatus": "ringing", "CallSid": "CA1"}
        assert twilio_voz.assinatura_valida(url, params, self._assinar(url, params)) is True

    def test_recusa_assinatura_de_outra_url(self, monkeypatch):
        monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "token-real")
        params = {"CallStatus": "ringing"}
        assinatura = self._assinar(
            "http://interno/api/v1/webhooks/twilio/status/abc/ativista", params
        )
        url = f"{BASE}/status/abc/ativista"
        assert twilio_voz.assinatura_valida(url, params, assinatura) is False

    def test_recusa_sem_assinatura(self, monkeypatch):
        monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "token-real")
        assert twilio_voz.assinatura_valida(f"{BASE}/x", {}, "") is False

    def test_sem_auth_token_aceita_fora_de_producao(self, monkeypatch):
        monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "test-token")
        monkeypatch.setattr(settings, "APP_ENV", "development")
        assert twilio_voz.assinatura_valida(f"{BASE}/x", {}, "") is True

    def test_sem_auth_token_recusa_em_producao(self, monkeypatch):
        monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "")
        monkeypatch.setattr(settings, "APP_ENV", "production")
        assert twilio_voz.assinatura_valida(f"{BASE}/x", {}, "qualquer") is False


class TestTwiml:
    def test_confirmacao_pede_digito_e_aponta_para_conectar(self):
        ligacao_id = str(uuid.uuid4())
        raiz = _xml(twilio_voz.twiml_confirmacao(ligacao_id, "Campanha X", "Ana Ribeiro"))

        gather = raiz.find("Gather")
        assert gather is not None
        assert gather.get("numDigits") == "1"
        assert gather.get("action") == f"{BASE}/conectar/{ligacao_id}"
        assert gather.get("method") == "POST"
        assert gather.get("actionOnEmptyResult") == "true"
        assert gather.get("timeout") == "10"

        verbos = [(filho.tag, filho.get("length")) for filho in gather]
        assert verbos == [("Pause", "1"), ("Say", None), ("Pause", "5"), ("Say", None)]
        mensagem, lembrete = gather.findall("Say")
        for say in (mensagem, lembrete):
            assert say.get("language") == "pt-BR"
            assert say.get("loop") is None
            assert "Ana Ribeiro" in say.text
            assert "pressione 1" in say.text.lower()
        assert "Campanha X" in mensagem.text

    def test_conectar_disca_para_o_alvo_com_callback_da_perna_alvo(self, monkeypatch):
        monkeypatch.setattr(settings, "TELEFONE_TIMEOUT_TOQUE_SEG", 25)
        ligacao_id = str(uuid.uuid4())
        raiz = _xml(
            twilio_voz.twiml_conectar(ligacao_id, "+552138282045", "+5511988887777", "Ana Ribeiro")
        )

        assert "Ana Ribeiro" in raiz.find("Say").text
        dial = raiz.find("Dial")
        assert dial.get("callerId") == "+552138282045"
        assert dial.get("timeout") == "25"
        numero = dial.find("Number")
        assert numero.text == "+5511988887777"
        assert numero.get("statusCallback") == f"{BASE}/status/{ligacao_id}/alvo"
        assert numero.get("statusCallbackMethod") == "POST"
        assert set(numero.get("statusCallbackEvent").split()) == {
            "initiated",
            "ringing",
            "answered",
            "completed",
        }

    def test_encerrar_desliga(self):
        raiz = _xml(twilio_voz.twiml_encerrar("Até logo."))
        assert raiz.find("Say").text == "Até logo."
        assert raiz.find("Hangup") is not None

    def test_encerrar_sem_mensagem(self):
        raiz = _xml(twilio_voz.twiml_encerrar())
        assert raiz.find("Say") is None
        assert raiz.find("Hangup") is not None


class TestEventoDoCallback:
    def test_converte_status_duracao_e_call_sid(self):
        ligacao_id = uuid.uuid4()
        evento = twilio_voz.evento_do_callback(
            ligacao_id,
            PernaLigacaoEnum.ALVO,
            {"CallStatus": "completed", "CallDuration": "42", "CallSid": "CA9"},
        )
        assert evento.ligacao_id == ligacao_id
        assert evento.perna == PernaLigacaoEnum.ALVO
        assert evento.status == StatusChamadaEnum.COMPLETED
        assert evento.duracao_seg == 42
        assert evento.call_id == "CA9"

    def test_sem_duracao(self):
        evento = twilio_voz.evento_do_callback(
            uuid.uuid4(), PernaLigacaoEnum.ATIVISTA, {"CallStatus": "ringing"}
        )
        assert evento.duracao_seg is None

    @pytest.mark.parametrize("status", ["", "desconhecido"])
    def test_status_desconhecido_retorna_none(self, status):
        evento = twilio_voz.evento_do_callback(
            uuid.uuid4(), PernaLigacaoEnum.ATIVISTA, {"CallStatus": status}
        )
        assert evento is None
