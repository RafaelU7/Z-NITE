"""
Unit tests for /v1/setup/status and /v1/setup/empresa.

Uses fully-mocked SQLAlchemy sessions so that no local database is required.
The session mock controls the scalar count returned by `select(func.count())`,
letting us exercise both the "empty DB" and "already initialised" branches.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import get_async_session
from main import create_app


def _make_session(empresa_count: int) -> AsyncMock:
    """Return an AsyncMock that simulates a session with `empresa_count` empresas."""
    scalar_result = MagicMock()
    scalar_result.scalar.return_value = empresa_count

    session = AsyncMock()
    session.execute = AsyncMock(return_value=scalar_result)

    # For the POST /empresa path we also need flush/commit/refresh to succeed
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    def _refresh_side_effect(obj):
        # Give the ORM object a fake UUID id so the response builder works
        if not getattr(obj, "id", None):
            object.__setattr__(obj, "id", uuid.uuid4())

    session.refresh = AsyncMock(side_effect=_refresh_side_effect)
    session.add = MagicMock()
    return session


@pytest_asyncio.fixture
async def empty_db_client() -> AsyncIterator[AsyncClient]:
    """Client whose session reports zero empresas (setup_required=True)."""
    application = create_app()
    mock_session = _make_session(empresa_count=0)

    async def override() -> AsyncIterator[AsyncMock]:
        yield mock_session

    application.dependency_overrides[get_async_session] = override
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def existing_db_client() -> AsyncIterator[AsyncClient]:
    """Client whose session reports one empresa (setup_required=False)."""
    application = create_app()
    mock_session = _make_session(empresa_count=1)

    async def override() -> AsyncIterator[AsyncMock]:
        yield mock_session

    application.dependency_overrides[get_async_session] = override
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    application.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_setup_status_true_when_no_empresa(empty_db_client: AsyncClient) -> None:
    """GET /v1/setup/status → setup_required=True when no empresa exists."""
    response = await empty_db_client.get("/v1/setup/status")

    assert response.status_code == 200
    assert response.json() == {"setup_required": True}


@pytest.mark.asyncio
async def test_setup_status_false_when_empresa_exists(existing_db_client: AsyncClient) -> None:
    """GET /v1/setup/status → setup_required=False when empresa already exists."""
    response = await existing_db_client.get("/v1/setup/status")

    assert response.status_code == 200
    assert response.json() == {"setup_required": False}


@pytest.mark.asyncio
async def test_setup_empresa_409_when_already_initialised(existing_db_client: AsyncClient) -> None:
    """POST /v1/setup/empresa → 409 when an empresa already exists."""
    response = await existing_db_client.post(
        "/v1/setup/empresa",
        json={
            "empresa": {"nome_fantasia": "Mercado Novo"},
            "gerente": {"nome": "Gerente QA", "codigo_operador": "900", "pin": "1234"},
            "caixa_descricao": "Caixa 01 - Principal",
        },
    )

    assert response.status_code == 409
    assert "painel gerencial" in response.json()["detail"]


@pytest.mark.asyncio
async def test_setup_empresa_201_on_first_access(empty_db_client: AsyncClient) -> None:
    """POST /v1/setup/empresa → 201 and correct fields on first access."""
    response = await empty_db_client.post(
        "/v1/setup/empresa",
        json={
            "empresa": {"nome_fantasia": "Mercado QA"},
            "gerente": {"nome": "Gerente QA", "codigo_operador": "900", "pin": "1234"},
            "caixa_descricao": "Caixa 01 - Principal",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert "empresa_id" in body
    assert "gerente_id" in body
    assert "caixa_id" in body
    assert "Mercado QA" in body["mensagem"]