/**
 * Catálogo offline — cache de produtos em IndexedDB para uso sem internet.
 *
 * Estratégia lazy: produtos são cacheados à medida que são escaneados online.
 * Busca offline por EAN (codigo_barras_principal) ou por ID.
 */

import { getDB } from './db'
import type { ProdutoCatalogOffline } from './types'
import type { ProdutoDTO } from '@/shared/types/api'

/** Converte um ProdutoDTO do backend para o formato de cache offline. */
export function produtoDTOParaCatalog(dto: ProdutoDTO): ProdutoCatalogOffline {
  return {
    id: dto.id,
    sku: dto.sku,
    codigo_barras_principal: dto.codigo_barras_principal,
    descricao: dto.descricao,
    descricao_pdv: dto.descricao_pdv,
    marca: dto.marca,
    preco_venda: parseFloat(dto.preco_venda),
    unidade_codigo: dto.unidade_codigo,
    controla_estoque: dto.controla_estoque,
    ean_fator_quantidade: dto.ean_fator_quantidade,
    ncm: dto.ncm,
    cfop: dto.cfop,
    csosn: dto.csosn,
    cst_icms: dto.cst_icms,
    perfil_tributario_id: dto.perfil_tributario_id,
    atualizado_em: new Date().toISOString(),
  }
}

/** Armazena (ou atualiza) um produto no catálogo offline. */
export async function cacheProduto(dto: ProdutoDTO): Promise<void> {
  const db = await getDB()
  await db.put('catalogo_produtos', produtoDTOParaCatalog(dto))
}

/**
 * Busca produto no catálogo offline por EAN.
 * Tenta primeiro pelo índice de código de barras principal,
 * depois pelo id (caso o EAN seja o próprio UUID do produto).
 */
export async function buscarProdutoOffline(
  ean: string,
): Promise<ProdutoCatalogOffline | null> {
  const db = await getDB()

  const porEan = await db.getFromIndex('catalogo_produtos', 'by-ean', ean)
  if (porEan) return porEan

  // Fallback: tenta por id (útil em ambientes de teste)
  try {
    const porId = await db.get('catalogo_produtos', ean)
    return porId ?? null
  } catch {
    return null
  }
}

/** Remove produtos do catálogo mais antigos que `maxIdadeDias` dias. */
export async function limparCatalogoAntigo(maxIdadeDias = 30): Promise<void> {
  const db = await getDB()
  const corte = new Date()
  corte.setDate(corte.getDate() - maxIdadeDias)
  const corteISO = corte.toISOString()

  const todos = await db.getAll('catalogo_produtos')
  const tx = db.transaction('catalogo_produtos', 'readwrite')
  for (const produto of todos) {
    if (produto.atualizado_em < corteISO) {
      await tx.store.delete(produto.id)
    }
  }
  await tx.done
}
