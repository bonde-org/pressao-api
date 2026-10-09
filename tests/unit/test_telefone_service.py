import uuid
from types import SimpleNamespace

import pytest

from pressao_api.core.config import settings
from pressao_api.services.telefone_service import TelefoneService


@pytest.fixture
def servico():
    return TelefoneService()


def _iniciar(servico: TelefoneService, **kwargs):
    dados = {
        "telefone_origem": "+551140028922",
        "telefone_ativista": "+5511999990000",
        "telefone_alvo": "+5511988887777",
        "ligacao_id": str(uuid.uuid4()),
        "acao_id": str(uuid.uuid4()),
        "campanha_id": str(uuid.uuid4()),
    }
    dados.update(kwargs)
    return servico.iniciar_ligacao(**dados)


class TestDryRun:
    def test_credencial_placeholder_ativa_dry_run(self, servico, monkeypatch):
        monkeypatch.setattr(settings, "TWILIO_SANDBOX_MODE", False)
        monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "mock-sid")
        assert servico.modo_dry_run() is True

    def test_sandbox_ativa_dry_run_mesmo_com_credencial_real(self, servico, monkeypatch):
        monkeypatch.setattr(settings, "TWILIO_SANDBOX_MODE", True)
        monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC123")
        monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "token-real")
        assert servico.modo_dry_run() is True

    def test_iniciar_ligacao_em_dry_run_nao_chama_provedor(self, servico, monkeypatch):
        monkeypatch.setattr(settings, "TWILIO_SANDBOX_MODE", True)
        resultado = _iniciar(servico)
        assert resultado.sucesso is True
        assert resultado.dry_run is True
        assert resultado.provedor == "dry_run"
        assert resultado.call_id.startswith("dryrun-")

    def test_dry_run_aceita_campanha_sem_numero_de_origem(self, servico, monkeypatch):
        monkeypatch.setattr(settings, "TWILIO_SANDBOX_MODE", True)
        resultado = _iniciar(servico, telefone_origem=None)
        assert resultado.sucesso is True

    def test_api_key_placeholder_sem_auth_token_real_ativa_dry_run(self, servico, monkeypatch):
        monkeypatch.setattr(settings, "TWILIO_SANDBOX_MODE", False)
        monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC123")
        monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "")
        monkeypatch.setattr(settings, "TWILIO_API_KEY_SID", "mock-key")
        assert servico.modo_dry_run() is True

    def test_recusa_telefone_invalido(self, servico):
        with pytest.raises(ValueError):
            _iniciar(servico, telefone_ativista="123")


class _ClienteFalso:
    def __init__(self, erro: Exception | None = None):
        self.chamadas: list[dict] = []
        self.erro = erro
        self.calls = self

    def create(self, **kwargs):
        self.chamadas.append(kwargs)
        if self.erro:
            raise self.erro
        return SimpleNamespace(sid="CA123")


@pytest.fixture
def twilio_real(monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_SANDBOX_MODE", False)
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "token-real")
    monkeypatch.setattr(settings, "TWILIO_API_KEY_SID", "SK123")
    monkeypatch.setattr(settings, "TWILIO_API_KEY_SECRET", "segredo")
    monkeypatch.setattr(
        settings, "TWILIO_WEBHOOK_URL", "https://pressao.exemplo/api/v1/webhooks/twilio/"
    )
    monkeypatch.setattr(settings, "TELEFONE_TIMEOUT_TOQUE_SEG", 25)


class TestLigacaoReal:
    def test_liga_para_o_ativista_com_urls_publicas(self, servico, twilio_real, monkeypatch):
        cliente = _ClienteFalso()
        monkeypatch.setattr(servico, "_cliente", lambda: cliente)
        ligacao_id = str(uuid.uuid4())

        resultado = _iniciar(servico, ligacao_id=ligacao_id)

        assert resultado.sucesso is True
        assert resultado.dry_run is False
        assert resultado.provedor == "twilio"
        assert resultado.call_id == "CA123"
        base = "https://pressao.exemplo/api/v1/webhooks/twilio"
        kwargs = cliente.chamadas[0]
        assert kwargs["to"] == "+5511999990000"
        assert kwargs["from_"] == "+551140028922"
        assert kwargs["url"] == f"{base}/twiml/{ligacao_id}"
        assert kwargs["method"] == "POST"
        assert kwargs["status_callback"] == f"{base}/status/{ligacao_id}/ativista"
        assert kwargs["status_callback_method"] == "POST"
        assert set(kwargs["status_callback_event"]) == {
            "initiated",
            "ringing",
            "answered",
            "completed",
        }
        assert kwargs["timeout"] == 25

    def test_erro_do_twilio_vira_falha(self, servico, twilio_real, monkeypatch):
        from twilio.base.exceptions import TwilioRestException

        erro = TwilioRestException(status=400, uri="/Calls", msg="Número inválido", code=21211)
        monkeypatch.setattr(servico, "_cliente", lambda: _ClienteFalso(erro))

        resultado = _iniciar(servico)

        assert resultado.sucesso is False
        assert resultado.provedor == "twilio"
        assert "21211" in resultado.erro

    def test_webhook_url_sem_https_falha_sem_chamar(self, servico, twilio_real, monkeypatch):
        monkeypatch.setattr(settings, "TWILIO_WEBHOOK_URL", "/api/v1/webhooks/twilio")
        cliente = _ClienteFalso()
        monkeypatch.setattr(servico, "_cliente", lambda: cliente)

        resultado = _iniciar(servico)

        assert resultado.sucesso is False
        assert "TWILIO_WEBHOOK_URL" in resultado.erro
        assert cliente.chamadas == []

    def test_cliente_usa_api_key_quando_configurada(self, servico, twilio_real):
        cliente = servico._cliente()
        assert cliente.username == "SK123"
        assert cliente.password == "segredo"
        assert cliente.account_sid == "AC123"

    def test_cliente_usa_auth_token_sem_api_key(self, servico, twilio_real, monkeypatch):
        monkeypatch.setattr(settings, "TWILIO_API_KEY_SID", "")
        monkeypatch.setattr(settings, "TWILIO_API_KEY_SECRET", "")
        cliente = servico._cliente()
        assert cliente.username == "AC123"
        assert cliente.password == "token-real"


class TestRoteiro:
    def _acao(self, nome="Maria", anonimo=False):
        return SimpleNamespace(id=uuid.uuid4(), ativista_nome=nome, anonimo=anonimo)

    def test_aplica_placeholders_do_template(self, servico):
        template = SimpleNamespace(
            conteudo="Sou {ativista_nome}, peço que {alvo_nome} apoie a {campanha_nome}."
        )
        roteiro = servico.montar_roteiro(
            acao=self._acao(),
            alvo=SimpleNamespace(nome="Ciclana"),
            campanha=SimpleNamespace(nome="Campanha X"),
            template=template,
        )
        assert roteiro == "Sou Maria, peço que Ciclana apoie a Campanha X."

    def test_roteiro_padrao_usa_marcador_quando_ativista_anonimo(self, servico):
        roteiro = servico.montar_roteiro(
            acao=self._acao(nome=None, anonimo=True),
            alvo=SimpleNamespace(nome="Ciclana"),
            campanha=SimpleNamespace(nome="Campanha X"),
            template=None,
        )
        assert "[seu nome]" in roteiro
        assert "Ciclana" in roteiro
        assert "Campanha X" in roteiro
