"""DTOs do domínio Produto."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ProdutoDTO(BaseModel):
    id: UUID
    empresa_id: UUID
    sku: Optional[str] = None
    codigo_barras_principal: Optional[str] = None
    descricao: str
    descricao_pdv: Optional[str] = None
    marca: Optional[str] = None
    preco_venda: Decimal
    custo_medio: Optional[Decimal] = None
    unidade_codigo: Optional[str] = None
    controla_estoque: bool
    pesavel: bool
    perfil_tributario_id: Optional[UUID] = None
    # Campos fiscais para visualização rápida no PDV
    ncm: Optional[str] = None
    cfop: Optional[str] = None
    csosn: Optional[str] = None
    cst_icms: Optional[str] = None
    ativo: bool
    destaque_pdv: bool
    # Informações do EAN pesquisado (quando buscado por EAN)
    ean_pesquisado: Optional[str] = None
    ean_fator_quantidade: Decimal = Decimal("1")

    model_config = {"from_attributes": True}
