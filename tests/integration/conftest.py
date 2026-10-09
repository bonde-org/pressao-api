import pytest

from pressao_api.core.config import settings
from pressao_api.core.security import get_current_user
from pressao_api.main import app

MEMBROS_TELEFONE = [
    ("Ciclana de Tal", "11988880001", "Vereador", "PT"),
    ("Beltrano Silva", "11988880002", "Deputado", "PSOL"),
    ("Fulana Souza", "11988880003", "Senadora", "PSB"),
]


@pytest.fixture
def telefone_dry_run(monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_SANDBOX_MODE", True)


@pytest.fixture
def campanha_telefone(client, db_session, mock_admin, telefone_dry_run):
    """Campanha com número de origem, 3 alvos de telefone e 1 roteiro ativo."""
    app.dependency_overrides[get_current_user] = lambda: mock_admin

    campanha = client.post(
        "/api/v1/campanhas/",
        json={"nome": "Campanha Telefone", "telefone_origem": "+551140028922"},
    ).json()

    membros = {}
    for nome, contato, cargo, partido in MEMBROS_TELEFONE:
        resp = client.post(
            "/api/v1/alvos/",
            json={
                "nome": nome,
                "contato": contato,
                "tipo_contato": "telefone",
                "campanha_id": campanha["id"],
                "metadados": {"cargo": cargo, "partido": partido},
            },
        )
        assert resp.status_code == 201, resp.text
        membros[nome] = resp.json()

    template = client.post(
        "/api/v1/templates/",
        json={
            "campanha_id": campanha["id"],
            "canal": "telefone",
            "titulo": "Roteiro",
            "conteudo": "Olá, sou {ativista_nome} e peço que {alvo_nome} apoie a {campanha_nome}.",
        },
    )
    assert template.status_code == 201, template.text

    alvos = client.get(f"/api/v1/alvos/campanha/{campanha['id']}").json()
    agregado = next(
        a for a in alvos if a["modo"] == "agregado" and a["tipo_contato"] == "telefone"
    )

    return {
        "campanha": campanha,
        "agregado": agregado,
        "membros": membros,
        "template": template.json(),
    }
