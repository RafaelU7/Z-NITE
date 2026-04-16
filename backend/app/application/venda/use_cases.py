"""
Use cases do domínio Venda / PDV.

IniciarVendaUseCase       — POST /v1/vendas
AdicionarItemUseCase      — POST /v1/vendas/{id}/itens
RemoverItemUseCase        — DELETE /v1/vendas/{id}/itens/{item_id}
GetVendaUseCase           — GET  /v1/vendas/{id}
AdicionarPagamentoUseCase — POST /v1/vendas/{id}/pagamentos
FinalizarVendaUseCase     — POST /v1/vendas/{id}/finalizar

Fluxo de estoque:
  AdicionarItem  → reduz saldo_atual do local principal (SELECT FOR UPDATE)
  RemoverItem    → restaura saldo_atual (SELECT FOR UPDATE)
  Finalizar      → cria MovimentacaoEstoque (ledger audit trail)

Fluxo fiscal:
  Finalizar → cria DocumentoFiscal(status=PENDENTE) para worker assíncrono
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.application.fiscal.services.fiscal_service import FiscalService
from app.infrastructure.database.models.enums import (
    StatusSessaoCaixa,
    StatusVenda,
    TipoEmissao,
    TipoMovimentacaoEstoque,
)
from app.infrastructure.database.models.produto import Produto as ProdutoModel
from app.infrastructure.database.models.venda import ItemVenda, PagamentoVenda, Venda
from app.infrastructure.database.repositories.caixa_repository import CaixaRepository
from app.infrastructure.database.repositories.estoque_repository import EstoqueRepository
from app.infrastructure.database.repositories.produto_repository import ProdutoRepository
from app.infrastructure.database.repositories.venda_repository import VendaRepository

from .dto import (
    AdicionarItemRequest,
    AdicionarPagamentoRequest,
    FinalizarVendaRequest,
    IniciarVendaRequest,
    ItemVendaDTO,
    PagamentoDTO,
    VendaDTO,
)


# ---------------------------------------------------------------------------
# Helpers de conversão ORM → DTO
# ---------------------------------------------------------------------------


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.0001"))


def _quantity(value: object) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.001"))

def _item_to_dto(item: ItemVenda) -> ItemVendaDTO:
    return ItemVendaDTO(
        id=item.id,
        produto_id=item.produto_id,
        descricao_produto=item.descricao_produto,
        codigo_barras=item.codigo_barras,
        unidade=item.unidade,
        sequencia=item.sequencia,
        quantidade=_quantity(item.quantidade),
        preco_unitario=_money(item.preco_unitario),
        desconto_unitario=_money(item.desconto_unitario),
        total_item=_money(item.total_item),
        cancelado=item.cancelado,
    )


def _pagamento_to_dto(pag: PagamentoVenda) -> PagamentoDTO:
    return PagamentoDTO(
        id=pag.id,
        forma_pagamento=pag.forma_pagamento,
        valor=_money(pag.valor),
        troco=_money(pag.troco),
        nsu=pag.nsu,
        bandeira_cartao=pag.bandeira_cartao,
    )


def _venda_to_dto(venda: Venda) -> VendaDTO:
    return VendaDTO(
        id=venda.id,
        empresa_id=venda.empresa_id,
        sessao_caixa_id=venda.sessao_caixa_id,
        operador_id=venda.operador_id,
        numero_venda_local=venda.numero_venda_local,
        status=venda.status,
        tipo_emissao=venda.tipo_emissao,
        data_venda=venda.data_venda,
        total_bruto=_money(venda.total_bruto),
        total_desconto=_money(venda.total_desconto),
        total_liquido=_money(venda.total_liquido),
        chave_idempotencia=venda.chave_idempotencia,
        itens=[_item_to_dto(i) for i in (venda.itens or [])],
        pagamentos=[_pagamento_to_dto(p) for p in (venda.pagamentos or [])],
    )


async def _reload(repo: VendaRepository, venda_id: UUID, empresa_id: UUID) -> VendaDTO:
    """Recarrega a venda do banco após mutações para retornar estado atualizado."""
    venda = await repo.get_by_id_empresa(venda_id, empresa_id)
    if not venda:
        raise NotFoundError("Venda não encontrada após atualização.")
    return _venda_to_dto(venda)


# ---------------------------------------------------------------------------
# Use cases
# ---------------------------------------------------------------------------

class IniciarVendaUseCase:
    def __init__(
        self,
        venda_repo: VendaRepository,
        caixa_repo: CaixaRepository,
    ) -> None:
        self._venda_repo = venda_repo
        self._caixa_repo = caixa_repo

    async def execute(
        self,
        request: IniciarVendaRequest,
        empresa_id: UUID,
        operador_id: UUID,
    ) -> VendaDTO:
        # Idempotência — retorna a venda existente sem criar duplicata
        if request.chave_idempotencia:
            existente = await self._venda_repo.get_by_idempotencia(
                request.chave_idempotencia, empresa_id
            )
            if existente:
                return _venda_to_dto(existente)

        # Verifica sessão aberta
        sessao = await self._caixa_repo.get_sessao_by_id(
            request.sessao_caixa_id, empresa_id
        )
        if not sessao:
            raise NotFoundError("Sessão de caixa não encontrada.")
        if sessao.status != StatusSessaoCaixa.ABERTA:
            raise BusinessRuleError("Sessão de caixa não está aberta.")

        numero = await self._venda_repo.proximo_numero_local(request.sessao_caixa_id)

        venda = Venda(
            empresa_id=empresa_id,
            sessao_caixa_id=request.sessao_caixa_id,
            operador_id=operador_id,
            numero_venda_local=numero,
            status=StatusVenda.EM_ABERTO,
            data_venda=request.data_venda or datetime.now(timezone.utc),
            total_bruto=Decimal("0"),
            total_desconto=Decimal("0"),
            total_liquido=Decimal("0"),
            chave_idempotencia=request.chave_idempotencia or uuid4(),
            origem_pdv=request.origem_pdv,
        )
        venda = await self._venda_repo.save(venda)
        return VendaDTO(
            id=venda.id,
            empresa_id=venda.empresa_id,
            sessao_caixa_id=venda.sessao_caixa_id,
            operador_id=venda.operador_id,
            numero_venda_local=venda.numero_venda_local,
            status=venda.status,
            data_venda=venda.data_venda,
            total_bruto=_money(venda.total_bruto),
            total_desconto=_money(venda.total_desconto),
            total_liquido=_money(venda.total_liquido),
            chave_idempotencia=venda.chave_idempotencia,
            itens=[],
            pagamentos=[],
        )


class AdicionarItemUseCase:
    def __init__(
        self,
        venda_repo: VendaRepository,
        produto_repo: ProdutoRepository,
        estoque_repo: EstoqueRepository,
    ) -> None:
        self._venda_repo = venda_repo
        self._produto_repo = produto_repo
        self._estoque_repo = estoque_repo

    async def execute(
        self,
        venda_id: UUID,
        request: AdicionarItemRequest,
        empresa_id: UUID,
        operador_id: UUID,
    ) -> VendaDTO:
        venda = await self._venda_repo.get_by_id_empresa(venda_id, empresa_id)
        if not venda:
            raise NotFoundError("Venda não encontrada.")
        if venda.status != StatusVenda.EM_ABERTO:
            raise BusinessRuleError("Somente vendas em aberto podem receber itens.")

        produto = await self._produto_repo.get_by_id_empresa(
            request.produto_id, empresa_id
        )
        if not produto:
            raise NotFoundError("Produto não encontrado.")
        if produto.perfil_tributario is None or not produto.perfil_tributario.ativo:
            raise BusinessRuleError(
                "Produto sem perfil tributário válido para venda."
            )

        preco = (
            request.preco_unitario
            if request.preco_unitario is not None
            else Decimal(str(produto.preco_venda))
        )
        desconto = request.desconto_unitario
        quantidade = request.quantidade
        total = (preco - desconto) * quantidade

        # Controle de estoque — decrementa imediatamente com lock
        if produto.controla_estoque:
            await self._estoque_repo.reduzir_saldo_principal(
                produto.id, empresa_id, float(quantidade)
            )

        # Snapshot fiscal
        perfil = produto.perfil_tributario
        snapshot_fiscal: dict | None = None
        if perfil:
            snapshot_fiscal = {
                "id": str(perfil.id),
                "nome": perfil.nome,
                "ncm": perfil.ncm,
                "cest": perfil.cest,
                "origem": perfil.origem if isinstance(perfil.origem, str) else (perfil.origem.value if perfil.origem else None),
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

        sequencia = await self._venda_repo.proximo_sequencial_item(venda_id)
        unidade_codigo = produto.unidade.codigo if produto.unidade else None
        origem_val = (
            perfil.origem
            if perfil is None or isinstance(perfil.origem, str)
            else (perfil.origem.value if perfil.origem else None)
        )

        item = ItemVenda(
            empresa_id=empresa_id,
            venda_id=venda_id,
            produto_id=produto.id,
            perfil_tributario_id=perfil.id if perfil else None,
            descricao_produto=produto.descricao,
            codigo_barras=produto.codigo_barras_principal,
            unidade=unidade_codigo,
            sequencia=sequencia,
            quantidade=quantidade,
            preco_unitario=preco,
            custo_unitario=(
                Decimal(str(produto.custo_medio))
                if produto.custo_medio is not None
                else None
            ),
            desconto_unitario=desconto,
            total_item=total,
            ncm=perfil.ncm if perfil else None,
            cest=perfil.cest if perfil else None,
            cfop=perfil.cfop_saida_interna if perfil else None,
            origem=origem_val,
            csosn=perfil.csosn if perfil else None,
            cst_icms=perfil.cst_icms if perfil else None,
            aliq_icms=(
                float(perfil.aliq_icms) if perfil and perfil.aliq_icms is not None else None
            ),
            cst_pis=perfil.cst_pis if perfil else None,
            aliq_pis=(
                float(perfil.aliq_pis) if perfil and perfil.aliq_pis is not None else None
            ),
            cst_cofins=perfil.cst_cofins if perfil else None,
            aliq_cofins=(
                float(perfil.aliq_cofins) if perfil and perfil.aliq_cofins is not None else None
            ),
            snapshot_fiscal=snapshot_fiscal,
            cancelado=False,
        )
        self._venda_repo._session.add(item)
        await self._venda_repo._session.flush()

        await self._venda_repo.atualizar_totais(venda)
        return await _reload(self._venda_repo, venda_id, empresa_id)


class RemoverItemUseCase:
    def __init__(
        self,
        venda_repo: VendaRepository,
        estoque_repo: EstoqueRepository,
    ) -> None:
        self._venda_repo = venda_repo
        self._estoque_repo = estoque_repo

    async def execute(
        self,
        venda_id: UUID,
        item_id: UUID,
        empresa_id: UUID,
        operador_id: UUID,
    ) -> VendaDTO:
        venda = await self._venda_repo.get_by_id_empresa(venda_id, empresa_id)
        if not venda:
            raise NotFoundError("Venda não encontrada.")
        if venda.status != StatusVenda.EM_ABERTO:
            raise BusinessRuleError("Somente vendas em aberto podem ter itens removidos.")

        item = await self._venda_repo.get_item(item_id, venda_id)
        if not item:
            raise NotFoundError("Item não encontrado ou já cancelado.")

        # Consulta o produto para saber se controla estoque
        result = await self._venda_repo._session.execute(
            select(ProdutoModel).where(ProdutoModel.id == item.produto_id)
        )
        produto = result.scalar_one_or_none()

        if produto and produto.controla_estoque:
            await self._estoque_repo.aumentar_saldo_principal(
                produto.id, empresa_id, float(item.quantidade)
            )

        item.cancelado = True
        item.cancelado_em = datetime.now(timezone.utc)
        item.cancelado_por_id = operador_id
        await self._venda_repo._session.flush()

        await self._venda_repo.atualizar_totais(venda)
        return await _reload(self._venda_repo, venda_id, empresa_id)


class GetVendaUseCase:
    def __init__(self, repo: VendaRepository) -> None:
        self._repo = repo

    async def execute(self, venda_id: UUID, empresa_id: UUID) -> VendaDTO:
        venda = await self._repo.get_by_id_empresa(venda_id, empresa_id)
        if not venda:
            raise NotFoundError("Venda não encontrada.")
        return _venda_to_dto(venda)


class AdicionarPagamentoUseCase:
    def __init__(self, repo: VendaRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        venda_id: UUID,
        request: AdicionarPagamentoRequest,
        empresa_id: UUID,
    ) -> VendaDTO:
        venda = await self._repo.get_by_id_empresa(venda_id, empresa_id)
        if not venda:
            raise NotFoundError("Venda não encontrada.")
        if venda.status != StatusVenda.EM_ABERTO:
            raise BusinessRuleError("Não é possível adicionar pagamento a esta venda.")

        pagamento = PagamentoVenda(
            empresa_id=empresa_id,
            venda_id=venda_id,
            forma_pagamento=request.forma_pagamento,
            valor=request.valor,
            troco=request.troco,
            nsu=request.nsu,
            bandeira_cartao=request.bandeira_cartao,
            autorizacao_cartao=request.autorizacao_cartao,
        )
        self._repo._session.add(pagamento)
        await self._repo._session.flush()
        return await _reload(self._repo, venda_id, empresa_id)


class FinalizarVendaUseCase:
    def __init__(
        self,
        venda_repo: VendaRepository,
        estoque_repo: EstoqueRepository,
        fiscal_service: FiscalService,
    ) -> None:
        self._venda_repo = venda_repo
        self._estoque_repo = estoque_repo
        self._fiscal_service = fiscal_service

    async def execute(
        self,
        venda_id: UUID,
        empresa_id: UUID,
        operador_id: UUID,
        tipo_emissao: TipoEmissao = TipoEmissao.FISCAL,
    ) -> VendaDTO:
        venda = await self._venda_repo.get_by_id_empresa(venda_id, empresa_id)
        if not venda:
            raise NotFoundError("Venda não encontrada.")
        if venda.status != StatusVenda.EM_ABERTO:
            raise BusinessRuleError("Venda não está em aberto.")

        itens_ativos = [i for i in (venda.itens or []) if not i.cancelado]
        if not itens_ativos:
            raise BusinessRuleError("Venda sem itens. Não é possível finalizar.")

        # Valida cobertura do pagamento
        total_pago = sum(Decimal(str(p.valor)) for p in (venda.pagamentos or []))
        total_venda = Decimal(str(venda.total_liquido))
        if total_pago < total_venda:
            raise BusinessRuleError(
                f"Pagamento insuficiente. "
                f"Total da venda: R$ {total_venda:.2f}, "
                f"Total pago: R$ {total_pago:.2f}."
            )

        # Cria registros de movimentação de estoque para auditoria
        for item in itens_ativos:
            result = await self._venda_repo._session.execute(
                select(ProdutoModel).where(ProdutoModel.id == item.produto_id)
            )
            produto = result.scalar_one_or_none()

            if produto and produto.controla_estoque:
                estoque = await self._estoque_repo.get_estoque_principal(
                    produto.id, empresa_id
                )
                if estoque:
                    saldo_pos = float(estoque.saldo_atual)
                    saldo_ant = saldo_pos + float(item.quantidade)
                    await self._estoque_repo.criar_movimentacao(
                        empresa_id=empresa_id,
                        produto_id=produto.id,
                        local_estoque_id=estoque.local_estoque_id,
                        usuario_id=operador_id,
                        tipo=TipoMovimentacaoEstoque.SAIDA_VENDA,
                        quantidade=float(item.quantidade),
                        saldo_anterior=saldo_ant,
                        saldo_posterior=saldo_pos,
                        custo_unitario=(
                            float(item.custo_unitario)
                            if item.custo_unitario is not None
                            else None
                        ),
                        referencia_tipo="venda",
                        referencia_id=venda_id,
                    )

        venda.status = StatusVenda.CONCLUIDA
        venda.tipo_emissao = tipo_emissao
        await self._venda_repo._session.flush()

        # Delega ao FiscalService a decisão de criar (FISCAL) ou não (GERENCIAL) o documento
        doc = await self._fiscal_service.processar_venda(venda)

        resultado = await _reload(self._venda_repo, venda_id, empresa_id)
        return resultado.model_copy(update={"documento_fiscal_id": doc.id if doc else None})
