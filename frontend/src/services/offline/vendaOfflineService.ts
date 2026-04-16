/**
 * Serviço de vendas offline — todas as operações CRUD na venda local
 * persistida em IndexedDB durante o modo offline do PDV.
 *
 * Cada operação é atômica dentro do IndexedDB.
 * O estado nunca é removido antes da confirmação do backend.
 */

import { v4 as uuidv4 } from 'uuid'
import { getDB } from './db'
import type {
  VendaOffline,
  ItemVendaOffline,
  PagamentoOffline,
  StatusLocalVenda,
} from './types'
import type { FormaPagamento, VendaDTO, TipoEmissao } from '@/shared/types/api'

// ---------------------------------------------------------------------------
// Contadores locais
// ---------------------------------------------------------------------------

const COUNTER_PREFIX = 'numero_venda_offline_'

async function proximoNumeroLocal(sessaoCaixaId: string): Promise<number> {
  const db = await getDB()
  const key = `${COUNTER_PREFIX}${sessaoCaixaId}`
  const entry = await db.get('contador_local', key)
  const proximo = (entry?.valor ?? 0) + 1
  await db.put('contador_local', { id: key, valor: proximo })
  return proximo
}

// ---------------------------------------------------------------------------
// Recálculo de totais
// ---------------------------------------------------------------------------

function recalcularTotais(venda: VendaOffline): VendaOffline {
  const ativos = venda.itens.filter((i) => !i.cancelado)
  const total_bruto = ativos.reduce((s, i) => s + i.preco_unitario * i.quantidade, 0)
  const total_desconto = ativos.reduce((s, i) => s + i.desconto_unitario * i.quantidade, 0)
  const total_liquido = total_bruto - total_desconto
  return { ...venda, total_bruto, total_desconto, total_liquido }
}

// ---------------------------------------------------------------------------
// Conversão VendaOffline → VendaDTO (para uso pelos componentes do PDV)
// ---------------------------------------------------------------------------

export function vendaOfflineParaDTO(venda: VendaOffline): VendaDTO {
  return {
    id: venda.venda_id,
    empresa_id: venda.empresa_id,
    sessao_caixa_id: venda.sessao_caixa_id,
    operador_id: venda.operador_id,
    numero_venda_local: venda.numero_venda_local,
    status: venda.status_local === 'em_aberto' ? 'em_aberto' : 'concluida',
    tipo_emissao: venda.tipo_emissao ?? 'FISCAL',
    data_venda: venda.data_venda,
    total_bruto: venda.total_bruto.toFixed(4),
    total_desconto: venda.total_desconto.toFixed(4),
    total_liquido: venda.total_liquido.toFixed(4),
    chave_idempotencia: venda.chave_idempotencia,
    itens: venda.itens.map((i) => ({
      id: i.id,
      produto_id: i.produto_id,
      descricao_produto: i.descricao_produto,
      codigo_barras: i.codigo_barras,
      unidade: i.unidade,
      sequencia: i.sequencia,
      quantidade: i.quantidade.toFixed(3),
      preco_unitario: i.preco_unitario.toFixed(4),
      desconto_unitario: i.desconto_unitario.toFixed(4),
      total_item: i.total_item.toFixed(4),
      cancelado: i.cancelado,
    })),
    pagamentos: venda.pagamentos.map((p) => ({
      id: p.id,
      forma_pagamento: p.forma_pagamento,
      valor: p.valor.toFixed(4),
      troco: p.troco.toFixed(4),
      nsu: p.nsu,
      bandeira_cartao: p.bandeira_cartao,
    })),
  }
}

// ---------------------------------------------------------------------------
// CRUD de venda offline
// ---------------------------------------------------------------------------

export async function criarVendaOffline(
  sessaoCaixaId: string,
  origemPdv: string,
  empresaId: string,
  operadorId: string,
): Promise<VendaOffline> {
  const numero = await proximoNumeroLocal(sessaoCaixaId)

  const venda: VendaOffline = {
    venda_id: uuidv4(),
    chave_idempotencia: uuidv4(),
    sessao_caixa_id: sessaoCaixaId,
    origem_pdv: origemPdv,
    data_venda: new Date().toISOString(),
    numero_venda_local: numero,
    itens: [],
    pagamentos: [],
    total_bruto: 0,
    total_desconto: 0,
    total_liquido: 0,
    status_local: 'em_aberto',
    tipo_emissao: 'FISCAL',
    erro_sync: null,
    empresa_id: empresaId,
    operador_id: operadorId,
    criado_em: new Date().toISOString(),
    sincronizado_em: null,
  }

  const db = await getDB()
  await db.put('vendas_offline', venda)
  return venda
}

export async function getVendaOffline(vendaId: string): Promise<VendaOffline | null> {
  const db = await getDB()
  return (await db.get('vendas_offline', vendaId)) ?? null
}

export async function getVendaOfflineEmAberto(
  sessaoCaixaId: string,
): Promise<VendaOffline | null> {
  const db = await getDB()
  const vendas = await db.getAllFromIndex('vendas_offline', 'by-status', 'em_aberto')
  return (
    vendas.find((venda) => venda.sessao_caixa_id === sessaoCaixaId) ?? null
  )
}

export async function adicionarItemOffline(
  vendaId: string,
  item: Omit<ItemVendaOffline, 'id' | 'sequencia'>,
): Promise<VendaOffline> {
  const db = await getDB()
  const venda: VendaOffline | undefined = await db.get('vendas_offline', vendaId)
  if (!venda) throw new Error('Venda offline não encontrada.')
  if (venda.status_local !== 'em_aberto')
    throw new Error('Venda offline não está em aberto.')

  const sequencia = venda.itens.filter((i) => !i.cancelado).length + 1
  const novoItem: ItemVendaOffline = { ...item, id: uuidv4(), sequencia }
  const atualizada = recalcularTotais({ ...venda, itens: [...venda.itens, novoItem] })
  await db.put('vendas_offline', atualizada)
  return atualizada
}

export async function removerItemOffline(
  vendaId: string,
  itemId: string,
): Promise<VendaOffline> {
  const db = await getDB()
  const venda: VendaOffline | undefined = await db.get('vendas_offline', vendaId)
  if (!venda) throw new Error('Venda offline não encontrada.')
  if (venda.status_local !== 'em_aberto')
    throw new Error('Venda offline não está em aberto.')

  const item = venda.itens.find((i) => i.id === itemId)
  if (!item) throw new Error('Item não encontrado.')

  const itens = venda.itens.map((i) =>
    i.id === itemId ? { ...i, cancelado: true } : i,
  )
  const atualizada = recalcularTotais({ ...venda, itens })
  await db.put('vendas_offline', atualizada)
  return atualizada
}

export async function adicionarPagamentoOffline(
  vendaId: string,
  forma: FormaPagamento,
  valor: number,
  troco = 0,
): Promise<VendaOffline> {
  const db = await getDB()
  const venda: VendaOffline | undefined = await db.get('vendas_offline', vendaId)
  if (!venda) throw new Error('Venda offline não encontrada.')
  if (venda.status_local !== 'em_aberto')
    throw new Error('Venda offline não está em aberto.')

  const pagamento: PagamentoOffline = {
    id: uuidv4(),
    forma_pagamento: forma,
    valor,
    troco,
    nsu: null,
    bandeira_cartao: null,
  }
  const atualizada = { ...venda, pagamentos: [...venda.pagamentos, pagamento] }
  await db.put('vendas_offline', atualizada)
  return atualizada
}

export async function finalizarVendaOffline(
  vendaId: string,
  tipoEmissao: TipoEmissao = 'FISCAL',
): Promise<VendaOffline> {
  const db = await getDB()
  const venda: VendaOffline | undefined = await db.get('vendas_offline', vendaId)
  if (!venda) throw new Error('Venda offline não encontrada.')
  if (venda.status_local !== 'em_aberto')
    throw new Error('Venda offline não está em aberto.')

  const ativos = venda.itens.filter((i) => !i.cancelado)
  if (ativos.length === 0)
    throw new Error('Venda sem itens. Não é possível finalizar.')

  const totalPago = venda.pagamentos.reduce((s, p) => s + p.valor, 0)
  // tolerância de 1 centavo para arredondamento
  if (totalPago < venda.total_liquido - 0.01) {
    throw new Error(
      `Pagamento insuficiente. Total: R$ ${venda.total_liquido.toFixed(2)}, Pago: R$ ${totalPago.toFixed(2)}.`,
    )
  }

  const atualizada: VendaOffline = { ...venda, status_local: 'pendente_sync', tipo_emissao: tipoEmissao }
  await db.put('vendas_offline', atualizada)
  return atualizada
}

// ---------------------------------------------------------------------------
// Consultas para sync
// ---------------------------------------------------------------------------

export async function getVendasPendentesSync(): Promise<VendaOffline[]> {
  const db = await getDB()
  return db.getAllFromIndex('vendas_offline', 'by-status', 'pendente_sync')
}

export async function getVendasComErro(): Promise<VendaOffline[]> {
  const db = await getDB()
  return db.getAllFromIndex('vendas_offline', 'by-status', 'erro_sync')
}

export async function countVendasPendentes(): Promise<number> {
  const db = await getDB()
  const pendentes = await db.getAllFromIndex('vendas_offline', 'by-status', 'pendente_sync')
  const erros = await db.getAllFromIndex('vendas_offline', 'by-status', 'erro_sync')
  return pendentes.length + erros.length
}

// ---------------------------------------------------------------------------
// Mutações de status para o ciclo de sync
// ---------------------------------------------------------------------------

export async function marcarSincronizando(vendaIds: string[]): Promise<void> {
  const db = await getDB()
  const tx = db.transaction('vendas_offline', 'readwrite')
  await Promise.all(
    vendaIds.map(async (id) => {
      const venda = await tx.store.get(id)
      if (venda) {
        await tx.store.put({
          ...venda,
          status_local: 'sincronizando' as StatusLocalVenda,
        })
      }
    }),
  )
  await tx.done
}

export async function marcarSincronizada(vendaId: string): Promise<void> {
  const db = await getDB()
  const venda = await db.get('vendas_offline', vendaId)
  if (!venda) return
  await db.put('vendas_offline', {
    ...venda,
    status_local: 'sincronizada' as StatusLocalVenda,
    sincronizado_em: new Date().toISOString(),
    erro_sync: null,
  })
}

export async function marcarErroSync(vendaId: string, motivo: string): Promise<void> {
  const db = await getDB()
  const venda = await db.get('vendas_offline', vendaId)
  if (!venda) return
  await db.put('vendas_offline', {
    ...venda,
    status_local: 'erro_sync' as StatusLocalVenda,
    erro_sync: motivo,
  })
}

export async function reenviarVendaErro(vendaId: string): Promise<void> {
  const db = await getDB()
  const venda = await db.get('vendas_offline', vendaId)
  if (!venda || venda.status_local !== 'erro_sync') return
  await db.put('vendas_offline', {
    ...venda,
    status_local: 'pendente_sync' as StatusLocalVenda,
    erro_sync: null,
  })
}
