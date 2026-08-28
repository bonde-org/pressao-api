from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from pressao_api.models.acao import Acao
from pressao_api.schemas.acao import CanalEnum, ProximoPassoTipoEnum, StatusAcaoEnum
from pressao_api.services.metricas import CalculadoraMetricas
from pressao_api.services.orquestrador import OrquestradorCanais


class TestMetricas:
    """Testes para calculadora de métricas."""

    def test_calcular_qualidade_suspeita(self):
        """Tempo < 5s deve ser suspeita."""
        qualidade = CalculadoraMetricas.calcular_qualidade(3)
        assert qualidade == "suspeita"

    def test_calcular_qualidade_alta(self):
        """Tempo entre 5s e 60s deve ser alta."""
        qualidade = CalculadoraMetricas.calcular_qualidade(30)
        assert qualidade == "alta"

    def test_calcular_qualidade_media(self):
        """Tempo entre 60s e 120s deve ser média."""
        qualidade = CalculadoraMetricas.calcular_qualidade(90)
        assert qualidade == "media"

    def test_calcular_qualidade_baixa(self):
        """Tempo > 120s deve ser baixa."""
        qualidade = CalculadoraMetricas.calcular_qualidade(150)
        assert qualidade == "baixa"

    def test_calcular_tempo_resposta(self):
        """Calcula tempo em segundos corretamente."""
        criado = datetime.now(UTC)
        confirmado = criado + timedelta(seconds=45)
        tempo = CalculadoraMetricas.calcular_tempo_resposta(criado, confirmado)
        assert tempo == 45


class TestOrquestrador:
    """Testes para orquestrador de canais."""

    @pytest.mark.asyncio
    async def test_estrategia_email(self):
        """Testa estratégia de email."""
        acao = Acao(
            id=uuid4(),
            ativista_id="test",
            campanha_id=uuid4(),
            alvo_id=uuid4(),
            canal=CanalEnum.EMAIL,
        )

        orquestrador = OrquestradorCanais()
        await orquestrador.executar(acao)

        assert acao.status == StatusAcaoEnum.PROCESSANDO
        assert acao.proximo_passo_tipo == ProximoPassoTipoEnum.WEBHOOK_AGUARDAR

    @pytest.mark.asyncio
    async def test_estrategia_whatsapp(self):
        """Testa estratégia de WhatsApp."""
        acao = Acao(
            id=uuid4(),
            ativista_id="test",
            campanha_id=uuid4(),
            alvo_id=uuid4(),
            canal=CanalEnum.WHATSAPP,
        )

        orquestrador = OrquestradorCanais()
        await orquestrador.executar(acao)

        assert acao.status == StatusAcaoEnum.AGUARDANDO_ACAO_HUMANA
        assert acao.proximo_passo_tipo == ProximoPassoTipoEnum.REDIRECIONAR_LINK
        assert "link" in acao.proximo_passo_dados

    @pytest.mark.asyncio
    async def test_estrategia_instagram(self):
        """Testa estratégia de Instagram."""
        acao = Acao(
            id=uuid4(),
            ativista_id="test",
            campanha_id=uuid4(),
            alvo_id=uuid4(),
            canal=CanalEnum.INSTAGRAM,
        )

        orquestrador = OrquestradorCanais()
        await orquestrador.executar(acao)

        assert acao.status == StatusAcaoEnum.AGUARDANDO_ACAO_HUMANA
        assert acao.proximo_passo_tipo == ProximoPassoTipoEnum.EXIBIR_TEXTO_E_ABRIR_PERFIL
        assert "texto" in acao.proximo_passo_dados
