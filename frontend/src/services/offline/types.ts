/**
 * Modelos locais para o modo offline do PDV Zênite.
 *
 * VendaOffline  — venda persistida em IndexedDB enquanto offline
 * ProdutoCatalogOffline — snapshot de produto armazenado para busca offline
 */

import type { FormaPagamento, TipoEmissao } from '@/shared/types/api'

// Status do ciclo de vida de uma venda offline
export type StatusLocalVenda =
  | 'em_aberto'       // sendo montada pelo operador
  | 'pendente_sync'   // finalizada localmente, aguardando sync
  | 'sincronizando'   // enviada para o backend, aguardando resposta
  | 'sincronizada'    // aceita pelo backend com sucesso
  | 'erro_sync'       // rejeitada pelo backend (ver erro_sync)

export interface ItemVendaOffline {
  id: string                              // UUID local
  produto_id: string
  descricao_produto: string
  codigo_barras: string | null
  unidade: string | null
  sequencia: number
  quantidade: number
  preco_unitario: number
  desconto_unitario: number
  total_item: number
  cancelado: boolean
  snapshot_fiscal: Record<string, unknown> | null  // preservado do momento da venda
}

export interface PagamentoOffline {
  id: string                              // UUID local
  forma_pagamento: FormaPagamento
  valor: number
  troco: number
  nsu: string | null
  bandeira_cartao: string | null
}

export interface VendaOffline {
  venda_id: string                        // UUID gerado localmente — chave primária
  chave_idempotencia: string              // UUID p/ dedup no backend ao sincronizar
  sessao_caixa_id: string
  origem_pdv: string
  data_venda: string                      // ISO 8601
  numero_venda_local: number              // Sequência local dentro da sessão offline
  itens: ItemVendaOffline[]
  pagamentos: PagamentoOffline[]
  total_bruto: number
  total_desconto: number
  total_liquido: number
  status_local: StatusLocalVenda
  tipo_emissao: TipoEmissao   // FISCAL = gera NFC-e no sync; GERENCIAL = sem documento fiscal
  erro_sync: string | null
  empresa_id: string
  operador_id: string
  criado_em: string
  sincronizado_em: string | null
}

export interface ProdutoCatalogOffline {
  id: string
  sku: string | null
  codigo_barras_principal: string | null
  descricao: string
  descricao_pdv: string | null
  marca: string | null
  preco_venda: number
  unidade_codigo: string | null
  controla_estoque: boolean
  ean_fator_quantidade: string
  ncm: string | null
  cfop: string | null
  csosn: string | null
  cst_icms: string | null
  perfil_tributario_id: string | null
  atualizado_em: string
}
