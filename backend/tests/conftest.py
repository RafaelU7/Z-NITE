from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.database import get_async_session
from app.infrastructure.database.models import Base
from app.infrastructure.database.models.caixa import Caixa
from app.infrastructure.database.models.empresa import Empresa
from app.infrastructure.database.models.enums import (
    AmbienteFiscal,
    OrigemMercadoria,
    PerfilUsuario,
    RegimeTributario,
    TipoUnidade,
)
from app.infrastructure.database.models.estoque import Estoque, LocalEstoque
from app.infrastructure.database.models.produto import Categoria, Produto, UnidadeMedida
from app.infrastructure.database.models.tributacao import PerfilTributario
from app.infrastructure.database.models.usuario import Usuario
from app.infrastructure.security.password_handler import hash_password, hash_pin
from app.infrastructure.security.redis_blacklist import get_redis
from main import create_app


class FakeRedis:
    def __init__(self) -> None:
        self._storage: dict[str, str] = {}

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._storage[key] = value

    async def exists(self, key: str) -> int:
        return 1 if key in self._storage else 0

    async def aclose(self) -> None:
        self._storage.clear()


def _build_test_urls() -> dict[str, str]:
    base_url = make_url(get_settings().database_url)
    test_database = f"{base_url.database}_test"
    admin_url = base_url.set(database="postgres")
    test_sync_url = base_url.set(database=test_database)
    test_async_url = str(test_sync_url).replace("postgresql://", "postgresql+asyncpg://", 1)
    return {
        "database_name": test_database,
        "admin_url": str(admin_url),
        "test_sync_url": str(test_sync_url),
        "test_async_url": test_async_url,
    }


async def _recreate_database(admin_url: str, database_name: str) -> None:
    url = make_url(admin_url)
    connection = await asyncpg.connect(
        user=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        database=url.database,
        ssl=False,
    )
    try:
        await connection.execute(
            "SELECT pg_terminate_backend(pid) "
            "FROM pg_stat_activity "
            "WHERE datname = $1 AND pid <> pg_backend_pid()",
            database_name,
        )
        await connection.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
        await connection.execute(f'CREATE DATABASE "{database_name}"')
    finally:
        await connection.close()


async def _drop_database(admin_url: str, database_name: str) -> None:
    url = make_url(admin_url)
    connection = await asyncpg.connect(
        user=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        database=url.database,
        ssl=False,
    )
    try:
        await connection.execute(
            "SELECT pg_terminate_backend(pid) "
            "FROM pg_stat_activity "
            "WHERE datname = $1 AND pid <> pg_backend_pid()",
            database_name,
        )
        await connection.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
    finally:
        await connection.close()


@pytest.fixture(scope="session")
def test_database_urls() -> dict[str, str]:
    return _build_test_urls()


@pytest.fixture(scope="session", autouse=True)
def _test_database_lifecycle(test_database_urls: dict[str, str]):
    import asyncio

    asyncio.run(
        _recreate_database(
            admin_url=test_database_urls["admin_url"],
            database_name=test_database_urls["database_name"],
        )
    )
    try:
        yield
    finally:
        asyncio.run(
            _drop_database(
                admin_url=test_database_urls["admin_url"],
                database_name=test_database_urls["database_name"],
            )
        )


@pytest.fixture(scope="session")
def test_sync_engine(test_database_urls: dict[str, str]):
    engine = create_engine(test_database_urls["test_sync_url"])
    try:
        yield engine
    finally:
        engine.dispose()


@pytest_asyncio.fixture
async def db_session(
    test_database_urls: dict[str, str],
    test_sync_engine,
) -> AsyncIterator[AsyncSession]:
    Base.metadata.drop_all(bind=test_sync_engine)
    Base.metadata.create_all(bind=test_sync_engine)

    test_engine = create_async_engine(
        test_database_urls["test_async_url"],
        echo=False,
        connect_args={"ssl": False},
    )

    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
    await test_engine.dispose()


@pytest_asyncio.fixture
async def seed_data(db_session: AsyncSession) -> dict[str, Any]:
    empresa = Empresa(
        razao_social="Empresa Teste LTDA",
        nome_fantasia="Zênite Teste",
        cnpj="12345678000195",
        inscricao_estadual="123456789",
        regime_tributario=RegimeTributario.SIMPLES_NACIONAL,
        ambiente_fiscal=AmbienteFiscal.HOMOLOGACAO,
        serie_nfce=1,
        serie_nfe=1,
        ativo=True,
    )
    db_session.add(empresa)
    await db_session.flush()

    gerente = Usuario(
        empresa_id=empresa.id,
        nome="Gerente Teste",
        email="gerente@teste.com",
        senha_hash=hash_password("senha123"),
        perfil=PerfilUsuario.GERENTE,
        codigo_operador="900",
        pin_hash=hash_pin("9999"),
        ativo=True,
    )
    operador = Usuario(
        empresa_id=empresa.id,
        nome="Operador Teste",
        email="operador@teste.com",
        senha_hash=hash_password("senha123"),
        perfil=PerfilUsuario.OPERADOR_CAIXA,
        codigo_operador="001",
        pin_hash=hash_pin("1234"),
        ativo=True,
    )
    db_session.add_all([gerente, operador])

    caixa = Caixa(
        empresa_id=empresa.id,
        numero=1,
        descricao="Caixa principal",
        numero_serie="CX-TESTE-001",
        ativo=True,
    )
    unidade = UnidadeMedida(
        empresa_id=empresa.id,
        codigo="UN",
        descricao="Unidade",
        tipo=TipoUnidade.UNITARIA,
        casas_decimais=0,
        ativo=True,
    )
    categoria = Categoria(
        empresa_id=empresa.id,
        nome="Mercearia",
        descricao="Categoria de teste",
        ativo=True,
    )
    db_session.add_all([caixa, unidade, categoria])
    await db_session.flush()

    perfil_tributario = PerfilTributario(
        empresa_id=empresa.id,
        nome="SN Alimentos",
        ativo=True,
        vigencia_inicio=date.today(),
        ncm="22021000",
        origem=OrigemMercadoria.NACIONAL,
        cfop_saida_interna="5102",
        cfop_saida_interestadual="6102",
        csosn="102",
        cst_pis="49",
        aliq_pis=Decimal("0.0000"),
        cst_cofins="49",
        aliq_cofins=Decimal("0.0000"),
    )
    perfil_tributario_inativo = PerfilTributario(
        empresa_id=empresa.id,
        nome="SN Inativo",
        ativo=False,
        vigencia_inicio=date.today(),
        vigencia_fim=date.today() + timedelta(days=1),
        ncm="22021000",
        origem=OrigemMercadoria.NACIONAL,
        cfop_saida_interna="5102",
        cfop_saida_interestadual="6102",
        csosn="102",
        cst_pis="49",
        aliq_pis=Decimal("0.0000"),
        cst_cofins="49",
        aliq_cofins=Decimal("0.0000"),
    )
    db_session.add_all([perfil_tributario, perfil_tributario_inativo])
    await db_session.flush()

    produto = Produto(
        empresa_id=empresa.id,
        sku="REF-001",
        codigo_barras_principal="7891234567890",
        descricao="Refrigerante Teste",
        descricao_pdv="REFRIG TESTE",
        marca="Zênite",
        categoria_id=categoria.id,
        unidade_id=unidade.id,
        pesavel=False,
        preco_venda=Decimal("10.00"),
        custo_medio=Decimal("4.50"),
        estoque_minimo=Decimal("1.000"),
        controla_estoque=True,
        perfil_tributario_id=perfil_tributario.id,
        ativo=True,
        destaque_pdv=True,
    )
    produto_inativo = Produto(
        empresa_id=empresa.id,
        sku="REF-002",
        codigo_barras_principal="7891234567891",
        descricao="Produto Inativo",
        descricao_pdv="INATIVO",
        marca="Zênite",
        categoria_id=categoria.id,
        unidade_id=unidade.id,
        pesavel=False,
        preco_venda=Decimal("12.00"),
        custo_medio=Decimal("5.00"),
        estoque_minimo=Decimal("1.000"),
        controla_estoque=True,
        perfil_tributario_id=perfil_tributario.id,
        ativo=False,
        destaque_pdv=False,
    )
    produto_sem_fiscal_valido = Produto(
        empresa_id=empresa.id,
        sku="REF-003",
        codigo_barras_principal="7891234567892",
        descricao="Produto Fiscal Inativo",
        descricao_pdv="FISCAL INV",
        marca="Zênite",
        categoria_id=categoria.id,
        unidade_id=unidade.id,
        pesavel=False,
        preco_venda=Decimal("9.50"),
        custo_medio=Decimal("3.50"),
        estoque_minimo=Decimal("1.000"),
        controla_estoque=True,
        perfil_tributario_id=perfil_tributario_inativo.id,
        ativo=True,
        destaque_pdv=False,
    )
    db_session.add_all([produto, produto_inativo, produto_sem_fiscal_valido])
    await db_session.flush()

    local_estoque = LocalEstoque(
        empresa_id=empresa.id,
        codigo="LOJA",
        descricao="Loja principal",
        principal=True,
        ativo=True,
    )
    db_session.add(local_estoque)
    await db_session.flush()

    db_session.add_all(
        [
            Estoque(
                empresa_id=empresa.id,
                produto_id=produto.id,
                local_estoque_id=local_estoque.id,
                saldo_atual=Decimal("10.000"),
                saldo_reservado=Decimal("0.000"),
                permite_negativo=False,
                versao=1,
                principal=True,
            ),
            Estoque(
                empresa_id=empresa.id,
                produto_id=produto_sem_fiscal_valido.id,
                local_estoque_id=local_estoque.id,
                saldo_atual=Decimal("5.000"),
                saldo_reservado=Decimal("0.000"),
                permite_negativo=False,
                versao=1,
                principal=True,
            ),
        ]
    )
    await db_session.flush()

    return {
        "empresa_id": empresa.id,
        "gerente": {
            "id": gerente.id,
            "email": gerente.email,
            "senha": "senha123",
            "codigo_operador": gerente.codigo_operador,
            "pin": "9999",
        },
        "operador": {
            "id": operador.id,
            "email": operador.email,
            "senha": "senha123",
            "codigo_operador": operador.codigo_operador,
            "pin": "1234",
        },
        "caixa_id": caixa.id,
        "produto_id": produto.id,
        "produto_ean": produto.codigo_barras_principal,
        "produto_inativo_ean": produto_inativo.codigo_barras_principal,
        "produto_sem_fiscal_valido_id": produto_sem_fiscal_valido.id,
        "local_estoque_id": local_estoque.id,
    }


@pytest_asyncio.fixture
async def app(db_session: AsyncSession, seed_data: dict[str, Any]) -> AsyncIterator[Any]:
    application = create_app()
    fake_redis = FakeRedis()

    async def override_get_async_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    async def override_get_redis() -> FakeRedis:
        return fake_redis

    application.dependency_overrides[get_async_session] = override_get_async_session
    application.dependency_overrides[get_redis] = override_get_redis
    try:
        yield application
    finally:
        application.dependency_overrides.clear()
        await fake_redis.aclose()


@pytest_asyncio.fixture
async def client(app: Any) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client