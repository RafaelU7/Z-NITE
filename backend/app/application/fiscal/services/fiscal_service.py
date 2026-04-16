"""
FiscalService — ponto central de decisão sobre emissão fiscal.

A lógica de EMITIR ou NÃO EMITIR documento fiscal fica AQUI.
Use cases e routers nunca fazem `if tipo_emissao == FISCAL` diretamente.

Fluxo:
  - FISCAL    → cria DocumentoFiscal(status=PENDENTE) para worker assíncrono
  - GERENCIAL → retorna None; nenhum documento é criado
"""
from __future__ import annotations

from typing import Optional

from app.infrastructure.database.models.enums import AmbienteFiscal, TipoEmissao
from app.infrastructure.database.models.fiscal import DocumentoFiscal
from app.infrastructure.database.models.venda import Venda
from app.infrastructure.database.repositories.fiscal_repository import FiscalRepository


class FiscalService:
    """
    Serviço desacoplado de processamento fiscal.

    Recebe uma venda já persistida (com id, empresa_id, operador_id e
    tipo_emissao atribuídos) e decide se um DocumentoFiscal deve ser criado.
    """

    def __init__(self, fiscal_repo: FiscalRepository) -> None:
        self._fiscal_repo = fiscal_repo

    async def processar_venda(
        self,
        venda: Venda,
        ambiente: AmbienteFiscal = AmbienteFiscal.HOMOLOGACAO,
    ) -> Optional[DocumentoFiscal]:
        """
        Cria DocumentoFiscal pendente se a venda for FISCAL.
        Retorna None para vendas GERENCIAL — sem efeitos colaterais.
        """
        if venda.tipo_emissao != TipoEmissao.FISCAL:
            return None

        return await self._fiscal_repo.criar_documento_pendente(
            empresa_id=venda.empresa_id,
            venda_id=venda.id,
            operador_id=venda.operador_id,
            ambiente=ambiente,
        )
