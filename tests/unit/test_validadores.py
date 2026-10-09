import pytest

from pressao_api.utils.validadores import (
    extrair_ddd,
    normalizar_telefone_e164,
    obter_mensagem_erro_compatibilidade,
    telefone_toll_free_br,
    validar_compatibilidade_canal_alvo,
    validar_email,
    validar_telefone,
)


class TestFormatoEmailTelefone:
    def test_validar_email_correto(self):
        assert validar_email("usuario@email.com") is True
        assert validar_email("nome.sobrenome@dominio.com.br") is True
        assert validar_email("user+tag@email.com") is True

    def test_validar_email_incorreto(self):
        assert validar_email("usuario@") is False
        assert validar_email("usuario@email") is False
        assert validar_email("usuario.email.com") is False
        assert validar_email("") is False

    def test_validar_telefone_correto(self):
        assert validar_telefone("(11) 99999-9999") is True
        assert validar_telefone("11999999999") is True
        assert validar_telefone("+55 11 99999-9999") is True

    def test_validar_telefone_incorreto(self):
        assert validar_telefone("12345") is False
        assert validar_telefone("abc") is False
        assert validar_telefone("") is False


class TestTelefoneE164:
    def test_normaliza_numero_nacional_com_ddi_padrao(self):
        assert normalizar_telefone_e164("(11) 99999-9999") == "+5511999999999"
        assert normalizar_telefone_e164("1133334444") == "+551133334444"

    def test_preserva_numero_com_ddi(self):
        assert normalizar_telefone_e164("+55 11 99999-9999") == "+5511999999999"
        assert normalizar_telefone_e164("5511999999999") == "+5511999999999"
        assert normalizar_telefone_e164("+1 415 123 4567") == "+14151234567"

    def test_recusa_numero_invalido(self):
        with pytest.raises(ValueError):
            normalizar_telefone_e164("12345")
        with pytest.raises(ValueError):
            normalizar_telefone_e164("")

    def test_extrai_ddd_de_numero_brasileiro(self):
        assert extrair_ddd("+5521988887777") == "21"
        assert extrair_ddd("+14151234567") is None
        assert extrair_ddd(None) is None

    def test_identifica_toll_free_brasileiro(self):
        assert telefone_toll_free_br("+558001234567") is True
        assert telefone_toll_free_br("+5511999999999") is False


class TestCompatibilidadeCanalAlvo:
    def test_compatibilidade_email_com_email(self):
        """Email é compatível com alvo do tipo email"""
        assert validar_compatibilidade_canal_alvo("email", "email") is True

    def test_compatibilidade_email_com_telefone(self):
        """Email NÃO é compatível com alvo do tipo telefone"""
        assert validar_compatibilidade_canal_alvo("email", "telefone") is False

    def test_compatibilidade_telefone_com_telefone(self):
        """Telefone é compatível com alvo do tipo telefone"""
        assert validar_compatibilidade_canal_alvo("telefone", "telefone") is True

    def test_compatibilidade_telefone_com_email(self):
        """Telefone NÃO é compatível com alvo do tipo email"""
        assert validar_compatibilidade_canal_alvo("telefone", "email") is False

    def test_compatibilidade_whatsapp_com_whatsapp(self):
        """WhatsApp é compatível com alvo do tipo whatsapp"""
        assert validar_compatibilidade_canal_alvo("whatsapp", "whatsapp") is True

    def test_compatibilidade_whatsapp_com_telefone(self):
        """WhatsApp NÃO é compatível com alvo do tipo telefone"""
        assert validar_compatibilidade_canal_alvo("whatsapp", "telefone") is False

    def test_compatibilidade_instagram_com_instagram(self):
        """Instagram é compatível com alvo do tipo instagram"""
        assert validar_compatibilidade_canal_alvo("instagram", "instagram") is True

    def test_compatibilidade_instagram_com_email(self):
        """Instagram NÃO é compatível com alvo do tipo email"""
        assert validar_compatibilidade_canal_alvo("instagram", "email") is False

    def test_compatibilidade_tiktok_com_tiktok(self):
        """TikTok é compatível com alvo do tipo tiktok"""
        assert validar_compatibilidade_canal_alvo("tiktok", "tiktok") is True

    def test_compatibilidade_tiktok_com_instagram(self):
        """TikTok NÃO é compatível com alvo do tipo instagram"""
        assert validar_compatibilidade_canal_alvo("tiktok", "instagram") is False

    def test_mensagem_erro_compatibilidade(self):
        """Testa mensagem de erro"""
        mensagem = obter_mensagem_erro_compatibilidade("email", "telefone")
        assert "email" in mensagem
        assert "telefone" in mensagem
        assert "não é compatível" in mensagem
