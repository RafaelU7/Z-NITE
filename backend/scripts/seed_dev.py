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

from sqlalchemy import select
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
from app.infrastructure.database.models.estoque import Estoque, LocalEstoque
from app.infrastructure.database.models.produto import Categoria, Produto, UnidadeMedida
from app.infrastructure.database.models.tributacao import PerfilTributario
from app.infrastructure.database.models.usuario import Usuario
from app.infrastructure.security.password_handler import hash_password, hash_pin


async def seed() -> None:
    settings = get_settings()
    async_url = settings.async_database_url
    engine = create_async_engine(async_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def get_one_or_none(session: AsyncSession, statement):
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async with factory() as session:
        # ── Empresa ──────────────────────────────────────────────────────────
        empresa = await get_one_or_none(
            session,
            select(Empresa).where(Empresa.cnpj == "12345678000195"),
        )
        if not empresa:
            empresa = Empresa(cnpj="12345678000195")
            session.add(empresa)
        empresa.razao_social = "Zênite Comércio LTDA"
        empresa.nome_fantasia = "Zênite PDV"
        empresa.inscricao_estadual = "123456789"
        empresa.regime_tributario = RegimeTributario.SIMPLES_NACIONAL
        empresa.ambiente_fiscal = AmbienteFiscal.HOMOLOGACAO
        empresa.serie_nfce = 1
        empresa.serie_nfe = 1
        empresa.ativo = True
        await session.flush()

        # ── Usuários ─────────────────────────────────────────────────────────
        gerente = await get_one_or_none(
            session,
            select(Usuario).where(Usuario.email == "admin@zenite.dev"),
        )
        if not gerente:
            gerente = Usuario(email="admin@zenite.dev")
            session.add(gerente)
        gerente.empresa_id = empresa.id
        gerente.nome = "Admin Zênite"
        gerente.senha_hash = hash_password("Admin@123")
        gerente.perfil = PerfilUsuario.GERENTE
        gerente.codigo_operador = "900"
        gerente.pin_hash = hash_pin("9999")
        gerente.ativo = True

        operador = await get_one_or_none(
            session,
            select(Usuario).where(Usuario.email == "operador@zenite.dev"),
        )
        if not operador:
            operador = Usuario(email="operador@zenite.dev")
            session.add(operador)
        operador.empresa_id = empresa.id
        operador.nome = "Operador PDV"
        operador.senha_hash = hash_password("Operador@123")
        operador.perfil = PerfilUsuario.OPERADOR_CAIXA
        operador.codigo_operador = "001"
        operador.pin_hash = hash_pin("1234")
        operador.ativo = True

        # ── Caixa ─────────────────────────────────────────────────────────────
        caixa = await get_one_or_none(
            session,
            select(Caixa).where(Caixa.empresa_id == empresa.id, Caixa.numero == 1),
        )
        if not caixa:
            caixa = Caixa(empresa_id=empresa.id, numero=1)
            session.add(caixa)
        caixa.descricao = "Caixa 01 - Principal"
        caixa.numero_serie = "CX-DEV-001"
        caixa.ativo = True
        # ── Unidade de medida ─────────────────────────────────────────────────
        unidade = await get_one_or_none(
            session,
            select(UnidadeMedida).where(
                UnidadeMedida.empresa_id == empresa.id,
                UnidadeMedida.codigo == "UN",
            ),
        )
        if not unidade:
            unidade = UnidadeMedida(empresa_id=empresa.id, codigo="UN")
            session.add(unidade)
        unidade.descricao = "Unidade"
        unidade.tipo = TipoUnidade.UNITARIA
        unidade.casas_decimais = 0
        unidade.ativo = True
        # ── Categoria ─────────────────────────────────────────────────────────
        categoria = await get_one_or_none(
            session,
            select(Categoria).where(
                Categoria.empresa_id == empresa.id,
                Categoria.nome == "Bebidas",
                Categoria.categoria_pai_id.is_(None),
            ),
        )
        if not categoria:
            categoria = Categoria(empresa_id=empresa.id, nome="Bebidas")
            session.add(categoria)
        categoria.descricao = "Bebidas em geral"
        categoria.ativo = True
        await session.flush()

        # ── Perfil tributário ──────────────────────────────────────────────────
        perfil_trib = await get_one_or_none(
            session,
            select(PerfilTributario).where(
                PerfilTributario.empresa_id == empresa.id,
                PerfilTributario.nome == "SN Alimentos",
            ),
        )
        if not perfil_trib:
            perfil_trib = PerfilTributario(empresa_id=empresa.id, nome="SN Alimentos")
            session.add(perfil_trib)
        perfil_trib.ativo = True
        perfil_trib.vigencia_inicio = date.today()
        perfil_trib.ncm = "22021000"
        perfil_trib.origem = OrigemMercadoria.NACIONAL
        perfil_trib.cfop_saida_interna = "5102"
        perfil_trib.cfop_saida_interestadual = "6102"
        perfil_trib.csosn = "102"
        perfil_trib.cst_pis = "49"
        perfil_trib.aliq_pis = Decimal("0.0000")
        perfil_trib.cst_cofins = "49"
        perfil_trib.aliq_cofins = Decimal("0.0000")
        await session.flush()

        # ── Local de estoque principal ────────────────────────────────────────
        local_principal = await get_one_or_none(
            session,
            select(LocalEstoque).where(
                LocalEstoque.empresa_id == empresa.id,
                LocalEstoque.principal.is_(True),
            ),
        )
        if not local_principal:
            local_principal = await get_one_or_none(
                session,
                select(LocalEstoque).where(
                    LocalEstoque.empresa_id == empresa.id,
                    LocalEstoque.codigo == "LOJA",
                ),
            )
        if not local_principal:
            local_principal = LocalEstoque(empresa_id=empresa.id, codigo="LOJA")
            session.add(local_principal)
        local_principal.descricao = "Loja Principal"
        local_principal.principal = True
        local_principal.ativo = True
        await session.flush()

        # ── Produtos de demonstração ───────────────────────────────────────────
        produtos_seed = [
            {
                "sku": "REF-001",
                "ean": "7891234567890",
                "descricao": "Refrigerante Cola 2L",
                "descricao_pdv": "REFRIG COLA 2L",
                "marca": "Zênite",
                "preco_venda": Decimal("8.99"),
                "custo_medio": Decimal("4.50"),
                "estoque_minimo": Decimal("5.000"),
                "saldo_inicial": Decimal("25.000"),
            },
            {
                "sku": "AGU-001",
                "ean": "7899999000001",
                "descricao": "Água Mineral 500ml",
                "descricao_pdv": "AGUA MINERAL 500ml",
                "marca": "Fonte Pura",
                "preco_venda": Decimal("2.50"),
                "custo_medio": Decimal("0.80"),
                "estoque_minimo": Decimal("10.000"),
                "saldo_inicial": Decimal("30.000"),
            },
            {
                "sku": "SNC-001",
                "ean": "7891111000003",
                "descricao": "Salgadinho Tradicional 100g",
                "descricao_pdv": "SALGADINHO 100g",
                "marca": "CrocCroc",
                "preco_venda": Decimal("4.75"),
                "custo_medio": Decimal("2.10"),
                "estoque_minimo": Decimal("3.000"),
                "saldo_inicial": Decimal("20.000"),
            },
        ]

        produtos: list[Produto] = []
        for produto_seed in produtos_seed:
            produto = await get_one_or_none(
                session,
                select(Produto).where(
                    Produto.empresa_id == empresa.id,
                    Produto.codigo_barras_principal == produto_seed["ean"],
                ),
            )
            if not produto:
                produto = Produto(
                    empresa_id=empresa.id,
                    sku=produto_seed["sku"],
                    codigo_barras_principal=produto_seed["ean"],
                )
                session.add(produto)

            produto.sku = produto_seed["sku"]
            produto.codigo_barras_principal = produto_seed["ean"]
            produto.descricao = produto_seed["descricao"]
            produto.descricao_pdv = produto_seed["descricao_pdv"]
            produto.marca = produto_seed["marca"]
            produto.categoria_id = categoria.id
            produto.unidade_id = unidade.id
            produto.pesavel = False
            produto.preco_venda = produto_seed["preco_venda"]
            produto.custo_medio = produto_seed["custo_medio"]
            produto.estoque_minimo = produto_seed["estoque_minimo"]
            produto.controla_estoque = True
            produto.perfil_tributario_id = perfil_trib.id
            produto.ativo = True
            produto.destaque_pdv = True
            produtos.append(produto)

        await session.flush()

        # ── Estoque principal dos produtos seedados ──────────────────────────
        for produto, produto_seed in zip(produtos, produtos_seed, strict=True):
            estoque = await get_one_or_none(
                session,
                select(Estoque).where(
                    Estoque.produto_id == produto.id,
                    Estoque.local_estoque_id == local_principal.id,
                ),
            )
            if not estoque:
                estoque = Estoque(
                    produto_id=produto.id,
                    local_estoque_id=local_principal.id,
                    empresa_id=empresa.id,
                )
                session.add(estoque)

            estoque.empresa_id = empresa.id
            estoque.saldo_atual = produto_seed["saldo_inicial"]
            estoque.saldo_reservado = Decimal("0.000")
            estoque.permite_negativo = False
            estoque.principal = True
            estoque.versao = max(int(estoque.versao or 1), 1)

        await session.commit()

        print("\n=== SEED CONCLUÍDO ===")
        print(f"EMPRESA_ID : {empresa.id}")
        print(f"CAIXA_ID   : {caixa.id}")
        print(f"LOCAL_ID   : {local_principal.id}")
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
