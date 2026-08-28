import random

from pressao_api.models.template import Template


def sortear_template(templates: list[Template]) -> Template | None:
    """Sorteia um template entre os disponíveis. None se a lista estiver vazia."""
    if not templates:
        return None
    return random.choice(templates)
