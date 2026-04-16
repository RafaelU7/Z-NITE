import api from './client'
import type { ProdutoDTO } from '@/shared/types/api'

export async function getProdutoByEAN(ean: string): Promise<ProdutoDTO> {
  const { data } = await api.get<ProdutoDTO>(`/produtos/ean/${ean}`)
  return data
}
