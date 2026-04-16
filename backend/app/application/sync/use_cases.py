"""
SincronizarVendasUseCase — processa um lote de vendas offline.

Para cada venda no lote:
  1. Verifica idempotência (chave_idempotencia já registrada → duplicada)
  2. Valida sessão de caixa (existência — não exige status ABERTA para
     permitir sync após fechamento de caixa)
  3. Cria a venda completa: cabeçalho + itens + pagamentos
  4. Finaliza a venda (status CONCLUIDA)
  5. Cria o DocumentoFiscal PENDENTE para o worker assíncrono
  6. Faz commit individual por venda (erros não cancelam todo o lote)

Cada venda é processada em sua própria transação de banco de dados.
O chamador (router) gerencia o ciclo de sessão.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.application.fiscal.services.fiscal_service import FiscalService
from app.infrastructure.database.models.enums import (
    StatusVenda,
    TipoMovimentacaoEstoque,
)
from app.infrastructure.database.models.venda import ItemVenda, PagamentoVenda, Venda
from app.infrastructure.database.repositories.caixa_repository import CaixaRepository
from app.infrastructure.database.repositories.estoque_repository import EstoqueRepository
from app.infrastructure.database.repositories.produto_repository import ProdutoRepository
from app.infrastructure.database.repositories.venda_repository import VendaRepository

from .dto import (
    SyncBatchRequest,
    SyncBatchResponse,
    SyncResultAceita,
    SyncResultDuplicada,
    SyncResultRejeitada,
    VendaSyncPayload,
)

logger = logging.getLogger(__name__)


class SincronizarVendasUseCase:
    def __init__(
        self,
        session: AsyncSession,
        venda_repo: VendaRepository,
        caixa_repo: CaixaRepository,
        produto_repo: ProdutoRepository,
        estoque_repo: EstoqueRepository,
        fiscal_service: FiscalService,
    ) -> None:
        self._session = session
        self._venda_repo = venda_repo
        self._caixa_repo = caixa_repo
        self._produto_repo = produto_repo
        self._estoque_repo = estoque_repo
        self._fiscal_service = fiscal_service

    async def execute(
        self,
        request: SyncBatchRequest,
        empresa_id: UUID,
        operador_id: UUID,
    ) -> SyncBatchResponse:
        aceitas: list[SyncResultAceita] = []
        duplicadas: list[SyncResultDuplicada] = []
        rejeitadas: list[SyncResultRejeitada] = []

        for payload in request.vendas:
            try:
                resultado = await self._processar_venda(
                    payload, empresa_id, operador_id
                )
                if resultado == "duplicada":
                    existente = await self._venda_repo.get_by_idempotencia(
                        payload.chave_idempotencia, empresa_id
                    )
                    duplicadas.append(
                        SyncResultDuplicada(
                            chave_idempotencia=payload.chave_idempotencia,
                            venda_id=existente.id,  # type: ignore[union-attr]
                        )
                    )
                else:
                    aceitas.append(resultado)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Sync: venda rejeitada chave=%s motivo=%s",
                    payload.chave_idempotencia,
                    str(exc),
                )
                # Reverte parcial da transação para esta venda
                await self._session.rollback()
                rejeitadas.append(
                    SyncResultRejeitada(
                        chave_idempotencia=payload.chave_idempotencia,
                        motivo=str(exc),
                    )
                )

        return SyncBatchResponse(
            aceitas=aceitas,
            duplicadas=duplicadas,
            rejeitadas=rejeitadas,
        )

    async def _processar_venda(
        self,
        payload: VendaSyncPayload,
        empresa_id: UUID,
        operador_id: UUID,
    ) -> SyncResultAceita | str:
        """
        Retorna o UUID da venda criada, ou a string "duplicada".
        Levanta exceção para qualquer erro de negócio.
        """
        # 1. Idempotência — evita duplicata
        existente = await self._venda_repo.get_by_idempotencia(
            payload.chave_idempotencia, empresa_id
        )
        if existente:
            return "duplicada"

        # 2. Valida sessão de caixa (existência, não exige status ABERTA)
        sessao = await self._caixa_repo.get_sessao_by_id(
            payload.sessao_caixa_id, empresa_id
        )
        if not sessao:
            raise BusinessRuleError(
                f"Sessão de caixa {payload.sessao_caixa_id} não encontrada."
            )

        # 3. Cria cabeçalho da venda
        numero = await self._venda_repo.proximo_numero_local(payload.sessao_caixa_id)
        data_venda = payload.data_venda or datetime.now(timezone.utc)

        venda = Venda(
            empresa_id=empresa_id,
            sessao_caixa_id=payload.sessao_caixa_id,
            operador_id=operador_id,
            numero_venda_local=numero,
            status=StatusVenda.EM_ABERTO,
            tipo_emissao=payload.tipo_emissao,
            data_venda=data_venda,
            total_bruto=Decimal("0"),
            total_desconto=Decimal("0"),
            total_liquido=Decimal("0"),
            chave_idempotencia=payload.chave_idempotencia,
            origem_pdv=payload.origem_pdv,
        )
        venda = await self._venda_repo.save(venda)

        # 4. Adiciona itens (usando preços do offline + snapshot fiscal atualizado)
        total_bruto = Decimal("0")
        total_desconto = Decimal("0")

        for item_payload in payload.itens:
            # Produto DEVE existir e ter perfil tributário ativo para garantir integridade fiscal
            produto = await self._produto_repo.get_by_id_empresa(
                item_payload.produto_id, empresa_id
            )
            if not produto:
                raise BusinessRuleError(
                    f"Produto {item_payload.produto_id} não encontrado. "
                    f"Não é possível sincronizar a venda."
                )
            if not produto.perfil_tributario or not produto.perfil_tributario.ativo:
                raise BusinessRuleError(
                    f"Produto '{produto.descricao}' não possui perfil tributário ativo. "
                    f"Contate o administrador."
                )

            perfil = produto.perfil_tributario
            preco = item_payload.preco_unitario
            desconto = item_payload.desconto_unitario
            quantidade = item_payload.quantidade
            total_item = (preco - desconto) * quantidade

            total_bruto += preco * quantidade
            total_desconto += desconto * quantidade

            # Ajuste de estoque se produto controla estoque
            if produto.controla_estoque:
                await self._estoque_repo.reduzir_saldo_principal(
                    produto.id, empresa_id, float(quantidade)
                )

            # Reconstrói snapshot fiscal a partir do perfil atual
            origem_val = (
                perfil.origem
                if isinstance(perfil.origem, str)
                else (perfil.origem.value if perfil.origem else None)
            )
            snapshot_fiscal = {
                "id": str(perfil.id),
                "nome": perfil.nome,
                "ncm": perfil.ncm,
                "cest": perfil.cest,
                "origem": origem_val,
                "cfop_saida_interna": perfil.cfop_saida_interna,
                "cfop_saida_interestadual": perfil.cfop_saida_interestadual,
                "csosn": perfil.csosn,
                "cst_icms": perfil.cst_icms,
                "aliq_icms": str(perfil.aliq_icms) if perfil.aliq_icms is not None else None,
                "cst_pis": perfil.cst_pis,
                "aliq_pis": str(perfil.aliq_pis) if perfil.aliq_pis is not None else None,
                "cst_cofins": perfil.cst_cofins,
                "aliq_cofins": str(perfil.aliq_cofins) if perfil.aliq_cofins is not None else None,
            }

            unidade = item_payload.unidade
            if produto.unidade:
                unidade = produto.unidade.codigo

            item = ItemVenda(
                empresa_id=empresa_id,
                venda_id=venda.id,
                produto_id=item_payload.produto_id,
                perfil_tributario_id=perfil.id,
                descricao_produto=item_payload.descricao_produto,
                codigo_barras=item_payload.codigo_barras,
                unidade=unidade,
                sequencia=item_payload.sequencia,
                quantidade=quantidade,
                preco_unitario=preco,
                desconto_unitario=desconto,
                total_item=total_item,
                snapshot_fiscal=snapshot_fiscal,
                # Campos fiscais individuais para queries eficientes
                ncm=perfil.ncm,
                cest=perfil.cest,
                cfop=perfil.cfop_saida_interna,
                origem=origem_val,
                csosn=perfil.csosn,
                cst_icms=perfil.cst_icms,
                aliq_icms=float(perfil.aliq_icms) if perfil.aliq_icms is not None else None,
                cst_pis=perfil.cst_pis,
                aliq_pis=float(perfil.aliq_pis) if perfil.aliq_pis is not None else None,
                cst_cofins=perfil.cst_cofins,
                aliq_cofins=float(perfil.aliq_cofins) if perfil.aliq_cofins is not None else None,
                cancelado=False,
            )
            self._session.add(item)

        # 5. Adiciona pagamentos
        total_pago = Decimal("0")
        for pag_payload in payload.pagamentos:
            pagamento = PagamentoVenda(
                empresa_id=empresa_id,
                venda_id=venda.id,
                forma_pagamento=pag_payload.forma_pagamento,
                valor=pag_payload.valor,
                troco=pag_payload.troco,
                nsu=pag_payload.nsu,
                bandeira_cartao=pag_payload.bandeira_cartao,
            )
            self._session.add(pagamento)
            total_pago += pag_payload.valor

        await self._session.flush()

        # 6. Atualiza totais da venda
        total_liquido = total_bruto - total_desconto
        if total_pago < total_liquido - Decimal("0.01"):
            raise BusinessRuleError(
                f"Pagamento insuficiente na venda offline. "
                f"Total: R$ {total_liquido:.2f}, Pago: R$ {total_pago:.2f}."
            )

        venda.total_bruto = total_bruto
        venda.total_desconto = total_desconto
        venda.total_liquido = total_liquido
        venda.status = StatusVenda.CONCLUIDA
        await self._session.flush()

        # 7. Cria movimentações de estoque para auditoria (ledger)
        await self._criar_movimentacoes_estoque(
            venda.id, empresa_id, operador_id, payload
        )

        # 8. Delega ao FiscalService a decisão de criar (FISCAL) ou não (GERENCIAL) o documento
        doc = await self._fiscal_service.processar_venda(venda)

        await self._session.commit()
        logger.info("Sync: venda aceita chave=%s venda_id=%s tipo_emissao=%s", payload.chave_idempotencia, venda.id, payload.tipo_emissao)
        return SyncResultAceita(
            chave_idempotencia=payload.chave_idempotencia,
            venda_id=venda.id,
            documento_fiscal_id=doc.id if doc else None,
        )

    async def _criar_movimentacoes_estoque(
        self,
        venda_id: UUID,
        empresa_id: UUID,
        operador_id: UUID,
        payload: VendaSyncPayload,
    ) -> None:
        """Registra movimentações de estoque (ledger) para auditoria."""
        for item_payload in payload.itens:
            produto = await self._produto_repo.get_by_id_empresa(
                item_payload.produto_id, empresa_id
            )
            if not produto or not produto.controla_estoque:
                continue

            estoque = await self._estoque_repo.get_estoque_principal(
                produto.id, empresa_id
            )
            if not estoque:
                continue

            saldo_pos = float(estoque.saldo_atual)
            saldo_ant = saldo_pos + float(item_payload.quantidade)

            await self._estoque_repo.criar_movimentacao(
                empresa_id=empresa_id,
                produto_id=produto.id,
                local_estoque_id=estoque.local_estoque_id,
                usuario_id=operador_id,
                tipo=TipoMovimentacaoEstoque.SAIDA_VENDA,
                quantidade=float(item_payload.quantidade),
                saldo_anterior=saldo_ant,
                saldo_posterior=saldo_pos,
                custo_unitario=None,
                referencia_tipo="venda",
                referencia_id=venda_id,
            )
