import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from pressao_api.core.database import Base, get_db  # ← Mudou
from pressao_api.core.security import get_current_user  # ← Mudou
from pressao_api.main import app  # ← Mudou de app.main para pressao_api.main

# Configuração para testes
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Engine para testes
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
def mock_user():
    return {"id": "test-user-123", "is_admin": False, "payload": {}}


@pytest.fixture
def mock_admin():
    return {"id": "admin-123", "is_admin": True, "payload": {}}


@pytest.fixture
def mock_service_account():
    return {
        "id": "service-account-123",
        "is_admin": True,
        "username": "service-account-pressao-api",
        "nome": "Service Account",
        "email": "service@pressao.com",
        "is_service": True,
        "payload": {},
    }


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator:
    """Cria sessão de banco para testes."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    # Limpa banco após teste
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def client(db_session):
    """Cria cliente de teste com dependências mockadas."""

    async def override_get_db():
        yield db_session

    def override_get_current_user():
        return {"id": "test-user-123", "is_admin": False}

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
