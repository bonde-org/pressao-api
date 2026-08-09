
import pytest

from pressao_api.models.campanha import Campanha
from pressao_api.schemas.campanha import CampanhaCreate


class TestCampanha:
    
    @pytest.mark.asyncio
    async def test_criar_campanha(self, db_session):
        campanha = Campanha(
            nome="Campanha Teste",
            descricao="Descrição da campanha",
            dominios_permitidos=["gmail.com", "yahoo.com"]
        )
        db_session.add(campanha)
        await db_session.commit()  # ← ADICIONAR await
        await db_session.refresh(campanha)  # ← ADICIONAR await para recarregar
        
        assert campanha.id is not None
        assert campanha.nome == "Campanha Teste"
        assert campanha.dominios_permitidos == ["gmail.com", "yahoo.com"]

    def test_validar_campanha_create(self):
        request = CampanhaCreate(
            nome="Campanha Válida",
            descricao="Descrição",
            dominios_permitidos=["dominio.com"]
        )
        assert request.nome == "Campanha Válida"