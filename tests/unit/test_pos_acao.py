import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from fastapi import BackgroundTasks

from pressao_api.models.acao import Acao
from pressao_api.models.campanha import Campanha
from pressao_api.schemas.campanha import CampanhaCreate, PosAcaoConfig
from pressao_api.services import actionnetwork, confirmacao_email, pos_acao
from pressao_api.services.email_service import EmailService

POS_ACAO = {
    "canais": ["email"],
    "actionnetwork": {"tags": ["tarifazero"]},
    "confirmacao_email": {
        "remetente_nome": "Annie do BONDE",
        "remetente_email": "mobilizacao@bonde.org",
        "assunto": "Tarifa Zero já - vamos chegar mais longe!",
        "texto": "Valeu, {nome}!\n\nAcesse www.tarifazero.bonde.org, pressione e compartilhe.",
    },
}


def _campanha(pos=POS_ACAO):
    return Campanha(id=uuid4(), nome="Tarifa Zero", pos_acao=pos)


def _acao(campanha, **kw):
    dados = {
        "id": uuid4(),
        "campanha_id": campanha.id,
        "alvo_id": uuid4(),
        "canal": "email",
        "ativista_nome": "Maria da Silva",
        "ativista_email": "Maria@Email.com",
        "ativista_telefone": "11999998888",
        "anonimo": False,
    }
    dados.update(kw)
    return Acao(**dados)


class TestSchema:
    def test_config_valida(self):
        c = CampanhaCreate(nome="Tarifa Zero", pos_acao=POS_ACAO)
        assert c.pos_acao.actionnetwork.tags == ["tarifazero"]

    def test_tags_vazias_rejeitadas(self):
        with pytest.raises(ValueError):
            PosAcaoConfig(actionnetwork={"tags": ["  "]})

    def test_remetente_invalido(self):
        cfg = dict(POS_ACAO["confirmacao_email"], remetente_email="nao-e-email")
        with pytest.raises(ValueError):
            PosAcaoConfig(confirmacao_email=cfg)


class TestMontarJob:
    def test_dispara_na_primeira_acao(self):
        c = _campanha()
        job = pos_acao.montar_job(_acao(c), c, primeira_acao=True)
        assert job and job.enviar_confirmacao is True

    def test_sem_confirmacao_nas_acoes_seguintes_mas_com_actionnetwork(self):
        c = _campanha()
        job = pos_acao.montar_job(_acao(c), c, primeira_acao=False)
        assert job and job.enviar_confirmacao is False

    @pytest.mark.parametrize(
        "kw", [{"anonimo": True}, {"ativista_email": None}, {"ativista_email": "invalido"}]
    )
    def test_ignora_anonimo_e_sem_email(self, kw):
        c = _campanha()
        assert pos_acao.montar_job(_acao(c, **kw), c, primeira_acao=True) is None

    def test_ignora_canal_fora_da_config_e_campanha_sem_pos_acao(self):
        c = _campanha()
        assert pos_acao.montar_job(_acao(c, canal="telefone"), c, primeira_acao=True) is None
        sem = _campanha(pos=None)
        assert pos_acao.montar_job(_acao(sem), sem, primeira_acao=True) is None


class TestAgendar:
    async def test_agenda_quando_primeira(self):
        c = _campanha()
        repo = MagicMock(contar_concluidas_por_email=AsyncMock(return_value=1))
        bt = BackgroundTasks()
        assert await pos_acao.agendar_pos_acao(bt, _acao(c), c, repo) is True
        assert len(bt.tasks) == 1

    async def test_nao_agenda_sem_config(self):
        c = _campanha(pos=None)
        repo = MagicMock(contar_concluidas_por_email=AsyncMock(return_value=1))
        bt = BackgroundTasks()
        assert await pos_acao.agendar_pos_acao(bt, _acao(c), c, repo) is False
        assert not bt.tasks

    async def test_erro_no_repo_nao_quebra_a_acao(self):
        c = _campanha()
        repo = MagicMock(contar_concluidas_por_email=AsyncMock(side_effect=RuntimeError("db")))
        assert await pos_acao.agendar_pos_acao(BackgroundTasks(), _acao(c), c, repo) is False


class TestExecutar:
    async def test_isola_falhas_entre_passos(self):
        c = _campanha()
        job = pos_acao.montar_job(_acao(c), c, primeira_acao=True)
        an = AsyncMock(side_effect=RuntimeError("an fora do ar"))
        conf = AsyncMock(return_value=True)
        with (
            patch.object(actionnetwork, "integracao_ativa", return_value=True),
            patch.object(actionnetwork, "registrar_contato", an),
            patch.object(pos_acao, "enviar_confirmacao", conf),
        ):
            await pos_acao.executar(job)
        an.assert_awaited_once()
        conf.assert_awaited_once()

    async def test_actionnetwork_desligado_sem_chave(self):
        c = _campanha()
        job = pos_acao.montar_job(_acao(c), c, primeira_acao=False)
        an = AsyncMock()
        with (
            patch.object(actionnetwork, "integracao_ativa", return_value=False),
            patch.object(actionnetwork, "registrar_contato", an),
        ):
            await pos_acao.executar(job)
        an.assert_not_awaited()


class TestActionNetwork:
    def test_payload(self):
        p = actionnetwork.montar_payload(
            "Maria da Silva Souza", " Maria@Email.com ", "(11) 99999-8888", ["tarifazero"]
        )
        assert p["add_tags"] == ["tarifazero"]
        pessoa = p["person"]
        assert pessoa["given_name"] == "Maria" and pessoa["family_name"] == "da Silva Souza"
        # não envia status: não reinscreve quem saiu da lista
        assert pessoa["email_addresses"] == [{"address": "maria@email.com"}]
        assert pessoa["phone_numbers"] == [{"number": "5511999998888"}]

    def test_payload_sem_telefone_invalido(self):
        p = actionnetwork.montar_payload("Ana", "ana@x.com", "123", ["t"])
        assert "phone_numbers" not in p["person"]

    async def test_sucesso_envia_token_e_corpo(self):
        visto = {}

        def handler(req: httpx.Request) -> httpx.Response:
            visto["url"], visto["token"] = str(req.url), req.headers.get("OSDI-API-Token")
            visto["body"] = json.loads(req.content)
            return httpx.Response(200, json={})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as cli:
            with patch.object(actionnetwork.settings, "ACTIONNETWORK_API_KEY", "segredo"):
                r = await actionnetwork.registrar_contato(
                    nome="Ana Lima",
                    email="ana@x.com",
                    telefone=None,
                    tags=["tarifazero"],
                    client=cli,
                )
        assert r.sucesso
        assert visto["url"] == "https://actionnetwork.org/api/v2/people/"
        assert visto["token"] == "segredo"
        assert visto["body"]["add_tags"] == ["tarifazero"]

    async def test_retenta_em_5xx_e_nao_em_4xx(self):
        chamadas = {"n": 0}

        def handler(req):
            chamadas["n"] += 1
            return httpx.Response(500 if chamadas["n"] < 3 else 200, json={})

        async def sem_espera(_):
            return None

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as cli:
            with (
                patch.object(actionnetwork.settings, "ACTIONNETWORK_API_KEY", "k"),
                patch.object(actionnetwork.asyncio, "sleep", sem_espera),
            ):
                r = await actionnetwork.registrar_contato(
                    nome="A", email="a@x.com", telefone=None, tags=["t"], client=cli
                )
        assert r.sucesso and chamadas["n"] == 3

        chamadas["n"] = 0

        def handler_4xx(req):
            chamadas["n"] += 1
            return httpx.Response(401, json={})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler_4xx)) as cli:
            with patch.object(actionnetwork.settings, "ACTIONNETWORK_API_KEY", "k"):
                r = await actionnetwork.registrar_contato(
                    nome="A", email="a@x.com", telefone=None, tags=["t"], client=cli
                )
        assert not r.sucesso and r.status_code == 401 and chamadas["n"] == 1

    async def test_sem_chave_nao_chama(self):
        with patch.object(actionnetwork.settings, "ACTIONNETWORK_API_KEY", ""):
            r = await actionnetwork.registrar_contato(
                nome="A", email="a@x.com", telefone=None, tags=["t"]
            )
        assert not r.sucesso


class TestConfirmacaoEmail:
    def _cfg(self):
        return PosAcaoConfig(**POS_ACAO).confirmacao_email

    def test_html_escapa_personaliza_e_linkifica(self):
        cfg = self._cfg()
        html = confirmacao_email.montar_html(cfg, "Maria da Silva")
        assert "Valeu, Maria!" in html
        assert '<a href="https://www.tarifazero.bonde.org">www.tarifazero.bonde.org</a>' in html
        assert html.count("<p") == 2

    def test_botao_whatsapp_no_html_e_no_texto(self):
        cfg = self._cfg().model_copy(
            update={"botao_whatsapp": "Pressione Hugo Motta! www.tarifazero.bonde.org"}
        )
        link = "https://wa.me/?text=Pressione%20Hugo%20Motta%21%20www.tarifazero.bonde.org"
        html = confirmacao_email.montar_html(cfg, "Maria")
        assert f'<a href="{link}"' in html and ">Compartilhe</a>" in html
        assert f"Compartilhe: {link}" in confirmacao_email.montar_texto(cfg, "Maria")

    def test_botao_no_lugar_do_marcador(self):
        cfg = self._cfg().model_copy(
            update={
                "texto": "Oi {nome}!\n\n[COMPARTILHE]\n\nSeguimos juntos!",
                "botao_whatsapp": "msg",
            }
        )
        html = confirmacao_email.montar_html(cfg, "Maria")
        assert html.index("Oi Maria!") < html.index("wa.me") < html.index("Seguimos juntos!")
        assert "[COMPARTILHE]" not in html and html.count("wa.me") == 1
        texto = confirmacao_email.montar_texto(cfg, "Maria")
        assert texto.index("wa.me") < texto.index("Seguimos") and "[COMPARTILHE]" not in texto

    def test_marcador_sem_mensagem_some(self):
        cfg = self._cfg().model_copy(update={"texto": "Oi\n\n{botao}\n\nTchau"})
        assert "{botao}" not in confirmacao_email.montar_html(cfg, None)
        assert "{botao}" not in confirmacao_email.montar_texto(cfg, None)

    def test_sem_mensagem_nao_ha_botao(self):
        cfg = self._cfg()
        assert "wa.me" not in confirmacao_email.montar_html(cfg, None)
        assert "wa.me" not in confirmacao_email.montar_texto(cfg, None)
        assert (
            PosAcaoConfig(
                confirmacao_email={**POS_ACAO["confirmacao_email"], "botao_whatsapp": "  "}
            ).confirmacao_email.botao_whatsapp
            is None
        )

    def test_html_escapa_conteudo(self):
        cfg = self._cfg().model_copy(update={"texto": "<script>x</script> oi"})
        assert "<script>" not in confirmacao_email.montar_html(cfg, None)

    async def test_envia_pelo_servico_sem_ids_de_acao(self):
        cfg = self._cfg()
        capturado = {}

        def falso(**kw):
            capturado.update(kw)
            return SimpleNamespace(sucesso=True, erro=None)

        with patch.object(confirmacao_email.email_service, "enviar_transacional", falso):
            ok = await confirmacao_email.enviar_confirmacao(
                cfg, nome="Maria", email="m@x.com", campanha_id="c1"
            )
        assert ok
        assert capturado["remetente_email"] == "mobilizacao@bonde.org"
        assert capturado["assunto"].startswith("Tarifa Zero já")
        assert "acao_id" not in capturado


class TestEnviarTransacional:
    def test_sandbox_dry_run_e_sem_acao_id(self):
        svc = EmailService(client=MagicMock())
        with (
            patch("pressao_api.services.email_service.settings") as st,
        ):
            st.SENDGRID_SANDBOX_MODE = True
            st.SENDGRID_API_KEY = "mock-key"
            r = svc.enviar_transacional(
                destinatario="m@x.com",
                remetente_email="mobilizacao@bonde.org",
                remetente_nome="Annie do BONDE",
                assunto="Oi",
                conteudo_html="<p>oi</p>",
                conteudo_texto="oi",
            )
        assert r.sucesso and r.sandbox
        svc._client.send.assert_not_called()

    def test_envio_real_leva_so_custom_args_de_tipo(self):
        cliente = MagicMock()
        cliente.send.return_value = SimpleNamespace(status_code=202, headers={"X-Message-Id": "m1"})
        svc = EmailService(client=cliente)
        with patch("pressao_api.services.email_service.settings") as st:
            st.SENDGRID_SANDBOX_MODE = False
            st.SENDGRID_API_KEY = "real"
            r = svc.enviar_transacional(
                destinatario="m@x.com",
                remetente_email="mobilizacao@bonde.org",
                remetente_nome="Annie do BONDE",
                assunto="Oi",
                conteudo_html="<p>oi</p>",
                conteudo_texto="oi",
                campanha_id="c1",
            )
        assert r.sucesso and r.message_id == "m1"
        mail = cliente.send.call_args[0][0].get()
        args = mail["custom_args"]
        assert args["tipo"] == "confirmacao_pos_acao"
        assert "acao_id" not in args and "disparo_id" not in args
