from uuid import uuid4

import pytest
from pydantic import ValidationError

from pressao_api.models.alvo import Alvo, TipoContato
from pressao_api.schemas.alvo import AlvoCreate


class TestAlvo:
    @pytest.mark.asyncio
    async def test_criar_alvo_email(self, db_session):
        alvo = Alvo(
            nome="João Silva",
            contato="joao@email.com",
            tipo_contato=TipoContato.EMAIL,
            campanha_id=uuid4(),
        )
        db_session.add(alvo)

        await db_session.commit()
        await db_session.refresh(alvo)

        assert alvo.id is not None
        assert alvo.tipo_contato == TipoContato.EMAIL

    def test_validar_telefone_invalido(self):
        """Telefone inválido deve falhar no schema"""
        with pytest.raises(ValidationError) as exc_info:
            AlvoCreate(
                nome="Maria Silva",
                contato="123",  # Telefone inválido
                tipo_contato=TipoContato.TELEFONE,
                campanha_id=uuid4(),
            )
        assert "Formato de telefone inválido" in str(exc_info.value)

    def test_validar_telefone_valido(self):
        """Telefone válido deve passar"""
        request = AlvoCreate(
            nome="Maria Silva",
            contato="11999999999",
            tipo_contato=TipoContato.TELEFONE,
            campanha_id=uuid4(),
        )
        assert request.contato == "11999999999"

    def test_validar_telefone_com_mascara(self):
        """Telefone com máscara deve passar"""
        request = AlvoCreate(
            nome="Maria Silva",
            contato="(11) 99999-9999",
            tipo_contato=TipoContato.TELEFONE,
            campanha_id=uuid4(),
        )
        assert request.contato == "(11) 99999-9999"
