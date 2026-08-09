from uuid import uuid4

import pytest

from pressao_api.models.acao import Acao
from pressao_api.repositories.acao_repository import AcaoRepository


class TestAcaoRepositoryAnonimo:
    """Testes do repositório com dados anônimos"""

    @pytest.mark.asyncio
    async def test_criar_acao_anonima(self, db_session):
        repo = AcaoRepository(db_session)

        acao_data = {
            "campanha_id": uuid4(),
            "alvo_id": uuid4(),
            "canal": "whatsapp",
            "status": "PROCESSANDO",
            "anonimo": True,
            # ✅ ativista_id não é necessário quando anonimo=True
        }

        acao = await repo.criar(acao_data)
        await db_session.commit()

        assert acao.anonimo is True
        assert acao.ativista_id is None
        assert acao.ativista_nome is None

    @pytest.mark.asyncio
    async def test_criar_acao_com_dados_ativista(self, db_session):
        repo = AcaoRepository(db_session)

        acao_data = {
            "campanha_id": uuid4(),
            "alvo_id": uuid4(),
            "canal": "email",
            "status": "PROCESSANDO",
            "ativista_nome": "João Silva",
            "ativista_email": "joao@email.com",
            "anonimo": False,
            # ✅ ativista_id não é obrigatório quando temos email
        }

        acao = await repo.criar(acao_data)
        await db_session.commit()

        assert acao.anonimo is False
        assert acao.ativista_nome == "João Silva"
        assert acao.ativista_email == "joao@email.com"

    @pytest.mark.asyncio
    async def test_criar_acao_com_ativista_id(self, db_session):
        repo = AcaoRepository(db_session)

        acao_data = {
            "campanha_id": uuid4(),
            "alvo_id": uuid4(),
            "canal": "instagram",
            "status": "PROCESSANDO",
            "ativista_id": "keycloak-123",
            "anonimo": False,
        }

        acao = await repo.criar(acao_data)
        await db_session.commit()

        assert acao.ativista_id == "keycloak-123"
        assert acao.anonimo is False

    @pytest.mark.asyncio
    async def test_buscar_acoes_por_email(self, db_session):
        AcaoRepository(db_session)

        email = "busca@email.com"

        # Cria duas ações com mesmo email
        for _ in range(3):
            acao = Acao(
                campanha_id=uuid4(),
                alvo_id=uuid4(),
                canal="email",
                status="PROCESSANDO",
                ativista_email=email,
                anonimo=False,
            )
            db_session.add(acao)
        await db_session.commit()

        # Busca ações por email (método a ser implementado)
        # acoes = await repo.buscar_por_email(email)
        # assert len(acoes) == 3
