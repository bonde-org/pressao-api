import random

from pressao_api.models.template import Template


def sortear_template(templates: list[Template]) -> Template | None:
    """Sorteia um template entre os disponíveis. None se a lista estiver vazia."""
    if not templates:
        return None
    return random.choice(templates)


def aplicar_placeholders(texto: str, valores: dict[str, str]) -> str:
    """
    Substitui `{chave}` pelos valores.

    Usa `replace` em vez de `str.format` porque templates autorais podem conter chaves
    literais (CSS inline, por exemplo).
    """
    for chave, valor in valores.items():
        texto = texto.replace("{" + chave + "}", valor)
    return texto
