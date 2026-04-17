"""
Seed script for development database.
Creates minimal data to test PDV login and sales flow.

Usage:
  cd backend
  $env:DATABASE_URL="postgresql://zenite@127.0.0.1:55432/zenite_pdv"
  $env:PYTHONPATH="."
  python scripts/seed_dev.py
"""
from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.infrastructure.database.models.caixa import Caixa
from app.infrastructure.database.models.empresa import Empresa
from app.infrastructure.database.models.enums import (
    AmbienteFiscal,
    OrigemMercadoria,
    PerfilUsuario,
    RegimeTributario,
    TipoUnidade,
)
from app.infrastructure.database.models.produto import Categoria, Produto, UnidadeMedida
from app.infrastructure.database.models.tributacao import PerfilTributario
from app.infrastructure.database.models.usuario import Usuario
from app.infrastructure.security.password_handler import hash_password, hash_pin


async def seed() -> None:
    settings = get_settings()
    async_url = settings.async_database_url
    engine = create_async_engine(async_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        # ── Empresa ──────────────────────────────────────────────────────────
        empresa = Empresa(
            razao_social="Zênite Comércio LTDA",
            nome_fantasia="Zênite PDV",
            cnpj="12345678000195",
            inscricao_estadual="123456789",
            regime_tributario=RegimeTributario.SIMPLES_NACIONAL,
            ambiente_fiscal=AmbienteFiscal.HOMOLOGACAO,
            serie_nfce=1,
            serie_nfe=1,
            ativo=True,
        )
        session.add(empresa)
        await session.flush()

        # ── Usuários ─────────────────────────────────────────────────────────
        gerente = Usuario(
            empresa_id=empresa.id,
            nome="Admin Zênite",
            email="admin@zenite.dev",
            senha_hash=hash_password("Admin@123"),
            perfil=PerfilUsuario.GERENTE,
            codigo_operador="900",
            pin_hash=hash_pin("9999"),
            ativo=True,
        )
        operador = Usuario(
            empresa_id=empresa.id,
            nome="Operador PDV",
            email="operador@zenite.dev",
            senha_hash=hash_password("Operador@123"),
            perfil=PerfilUsuario.OPERADOR_CAIXA,
            codigo_operador="001",
            pin_hash=hash_pin("1234"),
            ativo=True,
        )
        session.add_all([gerente, operador])

        # ── Caixa ─────────────────────────────────────────────────────────────
        caixa = Caixa(
            empresa_id=empresa.id,
            numero=1,
            descricao="Caixa 01 - Principal",
            numero_serie="CX-DEV-001",
            ativo=True,
        )
        # ── Unidade de medida ─────────────────────────────────────────────────
        unidade = UnidadeMedida(
            empresa_id=empresa.id,
            codigo="UN",
            descricao="Unidade",
            tipo=TipoUnidade.UNITARIA,
            casas_decimais=0,
            ativo=True,
        )
        # ── Categoria ─────────────────────────────────────────────────────────
        categoria = Categoria(
            empresa_id=empresa.id,
            nome="Bebidas",
            descricao="Bebidas em geral",
            ativo=True,
        )
        session.add_all([caixa, unidade, categoria])
        await session.flush()

        # ── Perfil tributário ──────────────────────────────────────────────────
        perfil_trib = PerfilTributario(
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
        session.add(perfil_trib)
        await session.flush()

        # ── Produtos de demonstração ───────────────────────────────────────────
        produtos = [
            Produto(
                empresa_id=empresa.id,
                sku="REF-001",
                codigo_barras_principal="7891234567890",
                descricao="Refrigerante Cola 2L",
                descricao_pdv="REFRIG COLA 2L",
                marca="Zênite",
                categoria_id=categoria.id,
                unidade_id=unidade.id,
                pesavel=False,
                preco_venda=Decimal("8.99"),
                custo_medio=Decimal("4.50"),
                estoque_minimo=Decimal("5.000"),
                controla_estoque=True,
                perfil_tributario_id=perfil_trib.id,
                ativo=True,
                destaque_pdv=True,
            ),
            Produto(
                empresa_id=empresa.id,
                sku="AGU-001",
                codigo_barras_principal="7899999000001",
                descricao="Água Mineral 500ml",
                descricao_pdv="AGUA MINERAL 500ml",
                marca="Fonte Pura",
                categoria_id=categoria.id,
                unidade_id=unidade.id,
                pesavel=False,
                preco_venda=Decimal("2.50"),
                custo_medio=Decimal("0.80"),
                estoque_minimo=Decimal("10.000"),
                controla_estoque=True,
                perfil_tributario_id=perfil_trib.id,
                ativo=True,
                destaque_pdv=True,
            ),
            Produto(
                empresa_id=empresa.id,
                sku="SNC-001",
                codigo_barras_principal="7891111000003",
                descricao="Salgadinho Tradicional 100g",
                descricao_pdv="SALGADINHO 100g",
                marca="CrocCroc",
                categoria_id=categoria.id,
                unidade_id=unidade.id,
                pesavel=False,
                preco_venda=Decimal("4.75"),
                custo_medio=Decimal("2.10"),
                estoque_minimo=Decimal("3.000"),
                controla_estoque=True,
                perfil_tributario_id=perfil_trib.id,
                ativo=True,
                destaque_pdv=True,
            ),
        ]
        session.add_all(produtos)
        await session.commit()

        print("\n=== SEED CONCLUÍDO ===")
        print(f"EMPRESA_ID : {empresa.id}")
        print(f"CAIXA_ID   : {caixa.id}")
        print()
        print("Operador de login:")
        print("  Código: 001")
        print("  PIN:    1234")
        print()
        print("Gerente:")
        print("  Código: 900")
        print("  PIN:    9999")
        print()
        print("Produtos (EAN):")
        for p in produtos:
            print(f"  {p.codigo_barras_principal}  {p.descricao_pdv}  R$ {p.preco_venda}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
