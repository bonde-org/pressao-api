import random
from uuid import uuid4

import pytest
import pytest_asyncio

from pressao_api.models.campanha import Campanha
from pressao_api.models.template import Template
from pressao_api.repositories.template_repository import TemplateRepository
from pressao_api.services.templates import sortear_template


def _template(campanha_id, canal="email", ativo=True, titulo="Titulo"):
    return Template(
        id=uuid4(),
        campanha_id=campanha_id,
        canal=canal,
        titulo=titulo,
        conteudo="<p>Conteudo</p>",
        ativo=ativo,
    )


class TestSortearTemplate:
    def test_lista_vazia_retorna_none(self):
        assert sortear_template([]) is None

    def test_template_unico_e_sempre_sorteado(self):
        template = _template(uuid4())
        assert sortear_template([template]) is template

    def test_sorteio_cobre_mais_de_um_template(self):
        campanha_id = uuid4()
        templates = [_template(campanha_id, titulo=f"Titulo {i}") for i in range(3)]

        random.seed(42)
        sorteados = {sortear_template(templates).id for _ in range(50)}

        assert len(sorteados) > 1

    def test_sorteio_devolve_item_da_lista(self):
        campanha_id = uuid4()
        templates = [_template(campanha_id, titulo=f"Titulo {i}") for i in range(4)]
        ids = {template.id for template in templates}

        for _ in range(20):
            assert sortear_template(templates).id in ids


class TestTemplateRepository:
    @pytest_asyncio.fixture
    async def campanha(self, db_session):
        campanha = Campanha(id=uuid4(), nome="Campanha Templates")
        db_session.add(campanha)
        await db_session.flush()
        return campanha

    async def test_listar_ativos_por_canal_ignora_inativos(self, db_session, campanha):
        repo = TemplateRepository(db_session)
        await repo.criar(
            {
                "campanha_id": campanha.id,
                "canal": "email",
                "titulo": "Ativo",
                "conteudo": "<p>Ativo</p>",
                "ativo": True,
            }
        )
        await repo.criar(
            {
                "campanha_id": campanha.id,
                "canal": "email",
                "titulo": "Inativo",
                "conteudo": "<p>Inativo</p>",
                "ativo": False,
            }
        )

        ativos = await repo.listar_ativos_por_canal(campanha.id, "email")

        assert [template.titulo for template in ativos] == ["Ativo"]

    async def test_listar_ativos_por_canal_ignora_outros_canais(self, db_session, campanha):
        repo = TemplateRepository(db_session)
        await repo.criar(
            {
                "campanha_id": campanha.id,
                "canal": "email",
                "titulo": "Email",
                "conteudo": "<p>Email</p>",
                "ativo": True,
            }
        )
        await repo.criar(
            {
                "campanha_id": campanha.id,
                "canal": "whatsapp",
                "titulo": "WhatsApp",
                "conteudo": "<p>WhatsApp</p>",
                "ativo": True,
            }
        )

        ativos = await repo.listar_ativos_por_canal(campanha.id, "email")

        assert [template.titulo for template in ativos] == ["Email"]

    async def test_listar_ativos_por_canal_ignora_outras_campanhas(self, db_session, campanha):
        outra = Campanha(id=uuid4(), nome="Outra Campanha")
        db_session.add(outra)
        await db_session.flush()

        repo = TemplateRepository(db_session)
        await repo.criar(
            {
                "campanha_id": outra.id,
                "canal": "email",
                "titulo": "De outra campanha",
                "conteudo": "<p>Outra</p>",
                "ativo": True,
            }
        )

        ativos = await repo.listar_ativos_por_canal(campanha.id, "email")

        assert ativos == []

    async def test_listar_por_campanha_sem_filtros_traz_tudo(self, db_session, campanha):
        repo = TemplateRepository(db_session)
        for canal, ativo in (("email", True), ("email", False), ("whatsapp", True)):
            await repo.criar(
                {
                    "campanha_id": campanha.id,
                    "canal": canal,
                    "titulo": f"{canal}-{ativo}",
                    "conteudo": "<p>Conteudo</p>",
                    "ativo": ativo,
                }
            )

        todos = await repo.listar_por_campanha(campanha.id)

        assert len(todos) == 3

    @pytest.mark.parametrize(
        ("canal", "ativo", "esperado"),
        [
            ("email", None, 2),
            ("email", True, 1),
            (None, True, 2),
            ("whatsapp", True, 1),
        ],
    )
    async def test_listar_por_campanha_aplica_filtros(
        self, db_session, campanha, canal, ativo, esperado
    ):
        repo = TemplateRepository(db_session)
        for canal_template, ativo_template in (
            ("email", True),
            ("email", False),
            ("whatsapp", True),
        ):
            await repo.criar(
                {
                    "campanha_id": campanha.id,
                    "canal": canal_template,
                    "titulo": f"{canal_template}-{ativo_template}",
                    "conteudo": "<p>Conteudo</p>",
                    "ativo": ativo_template,
                }
            )

        resultado = await repo.listar_por_campanha(campanha.id, canal=canal, ativo=ativo)

        assert len(resultado) == esperado
