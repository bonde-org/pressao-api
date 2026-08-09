import pytest
from uuid import uuid4
from pydantic import ValidationError
from pressao_api.schemas.acao import (
    CriarAcaoRequest,
    AtivistaInfo,
    CanalEnum
)

class TestAcaoAnonimaSchema:
    """Testes de validação do schema para ações anônimas"""

class TestAcaoAnonimaSchema:
    
    def test_criar_acao_nao_anonima_com_email(self):
        """Ação não anônima com email deve passar"""
        request = CriarAcaoRequest(
            campanha_id=uuid4(),
            alvo_id=uuid4(),
            canal=CanalEnum.EMAIL,
            ativista=AtivistaInfo(
                nome="João Silva",
                email="joao@email.com"
            )
        )
        assert request.anonimo is False
        assert request.ativista.email == "joao@email.com"

    def test_criar_acao_nao_anonima_com_telefone(self):
        """Ação não anônima com telefone deve passar"""
        request = CriarAcaoRequest(
            campanha_id=uuid4(),
            alvo_id=uuid4(),
            canal=CanalEnum.WHATSAPP,
            ativista=AtivistaInfo(
                nome="Maria Oliveira",
                telefone="1199999999"
            )
        )
        assert request.ativista.telefone == "1199999999"

    def test_criar_acao_nao_anonima_sem_identificador(self):
        """Ação não anônima sem email OU telefone deve falhar"""
        with pytest.raises(ValidationError) as exc_info:
            CriarAcaoRequest(
                campanha_id=uuid4(),
                alvo_id=uuid4(),
                canal=CanalEnum.EMAIL,
                ativista=AtivistaInfo(nome="Sem identificador")
            )
        assert "É necessário fornecer email ou telefone" in str(exc_info.value)
    
    def test_criar_acao_anonima_com_ativista_ignorado(self):
        """Se anonimo=True, dados do ativista são ignorados"""
        request = CriarAcaoRequest(
            campanha_id=uuid4(),
            alvo_id=uuid4(),
            canal=CanalEnum.WHATSAPP,
            anonimo=True,
            ativista=AtivistaInfo(
                nome="Ignorado",
                email="ignorado@email.com"
            )
        )
        assert request.anonimo is True

    def test_criar_acao_com_email_invalido(self):
        """Email inválido deve falhar"""
        with pytest.raises(ValidationError) as exc_info:
            CriarAcaoRequest(
                campanha_id=uuid4(),
                alvo_id=uuid4(),
                canal=CanalEnum.EMAIL,
                ativista=AtivistaInfo(
                    nome="João",
                    email="email-invalido"
                )
            )
        assert "Formato de e-mail inválido" in str(exc_info.value)

    def test_criar_acao_anonima_sem_ativista(self):
        """Ação anônima não precisa de dados do ativista"""
        request = CriarAcaoRequest(
            campanha_id=uuid4(),
            alvo_id=uuid4(),
            canal=CanalEnum.WHATSAPP,
            anonimo=True
        )
        assert request.anonimo is True
        assert request.ativista is None

    def test_criar_acao_nao_anonima_sem_ativista(self):
        """Ação não anônima sem ativista deve passar (dados virão do token)"""
        # Na vida real, o usuário logado fornece os dados
        # O schema não deve bloquear, pois o endpoint vai preencher
        request = CriarAcaoRequest(
            campanha_id=uuid4(),
            alvo_id=uuid4(),
            canal=CanalEnum.EMAIL
        )
        assert request.anonimo is False
        assert request.ativista is None
        # O endpoint preencherá com os dados do token