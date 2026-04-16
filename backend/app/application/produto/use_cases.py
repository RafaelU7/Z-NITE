"""
Use cases do domínio Produto.

GetProdutoByIdUseCase   — GET /v1/produtos/{produto_id}
GetProdutoByEANUseCase  — GET /v1/produtos/ean/{ean}
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.produto import Produto
from app.infrastructure.database.repositories.produto_repository import ProdutoRepository

from .dto import ProdutoDTO


def _to_dto(produto: Produto, ean_pesquisado: str | None = None, fator: float = 1.0) -> ProdutoDTO:
    perfil = produto.perfil_tributario
    unidade = produto.unidade
    return ProdutoDTO(
        id=produto.id,
        empresa_id=produto.empresa_id,
        sku=produto.sku,
        codigo_barras_principal=produto.codigo_barras_principal,
        descricao=produto.descricao,
        descricao_pdv=produto.descricao_pdv,
        marca=getattr(produto, "marca", None),
        preco_venda=Decimal(str(produto.preco_venda)),
        custo_medio=Decimal(str(produto.custo_medio)) if produto.custo_medio is not None else None,
        unidade_codigo=unidade.codigo if unidade else None,
        controla_estoque=produto.controla_estoque,
        pesavel=produto.pesavel,
        perfil_tributario_id=perfil.id if perfil else None,
        ncm=perfil.ncm if perfil else None,
        cfop=perfil.cfop_saida_interna if perfil else None,
        csosn=perfil.csosn if perfil else None,
        cst_icms=perfil.cst_icms if perfil else None,
        ativo=produto.ativo,
        destaque_pdv=produto.destaque_pdv,
        ean_pesquisado=ean_pesquisado,
        ean_fator_quantidade=Decimal(str(fator)),
    )


class GetProdutoByIdUseCase:
    def __init__(self, repo: ProdutoRepository) -> None:
        self._repo = repo

    async def execute(self, produto_id: UUID, empresa_id: UUID) -> ProdutoDTO:
        produto = await self._repo.get_by_id_empresa(produto_id, empresa_id)
        if not produto:
            raise NotFoundError("Produto não encontrado.")
        return _to_dto(produto)


class GetProdutoByEANUseCase:
    def __init__(self, repo: ProdutoRepository) -> None:
        self._repo = repo

    async def execute(self, ean: str, empresa_id: UUID) -> ProdutoDTO:
        result = await self._repo.get_by_ean(ean, empresa_id)
        if not result:
            raise NotFoundError("Produto não encontrado para o EAN informado.")
        produto, fator = result
        return _to_dto(produto, ean_pesquisado=ean, fator=fator)
